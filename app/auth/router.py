from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.csrf import register_csrf_field
from app.core.client_ip import client_ip
from app.core.config import settings
from app.core.deps import resolve_user
from app.core.security import (
    InvalidEmailError,
    InvalidPasswordError,
    PASSWORD_MIN_LENGTH,
    normalize_email,
    validate_password,
)
from app.services import rate_limit_service as rl
from app.db.session import get_session
from app.models.user import User
from app.services.auth_service import (
    RESET_TOKEN,
    VERIFY_TOKEN,
    EmailTakenError,
    UsernameTakenError,
    authenticate_user,
    create_token,
    create_user,
    delete_token,
    delete_user_tokens,
    get_user_by_email,
    get_user_by_token,
    is_email_verified,
    latest_token_created_at,
    mark_email_verified,
    reset_password,
)
from app.services.email_service import (
    send_password_reset_email,
    send_verification_email,
)
from app.services.signup_code_service import (
    refund_code,
    signup_allowed,
    signup_requires_code,
)

# Search auth templates first, plus the dashboard templates for the shared base.html.
_dashboard_templates = Path(__file__).parent.parent / "dashboard" / "templates"
templates = register_csrf_field(
    Jinja2Templates(
        directory=[str(Path(__file__).parent / "templates"), str(_dashboard_templates)]
    )
)
router = APIRouter(tags=["auth"])

COOKIE_MAX_AGE = settings.session_ttl_days * 24 * 60 * 60


def _set_session_cookie(response: RedirectResponse, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="login.html", context={})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    # Both keys, because either alone leaves a hole: per-IP misses a botnet working on
    # one account, per-account misses one host working through many accounts.
    ip = rl.ip_key(client_ip(request))
    account = rl.account_key(email)
    await rl.enforce(session, rl.LOGIN, ip, account)

    user = await authenticate_user(session, email, password)
    if user is None:
        await rl.record_failure(session, rl.LOGIN, ip, account)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "E-Mail-Adresse oder Passwort ist ungültig.",
                "email": email.strip(),
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    # A correct password clears the account's failures but deliberately not the IP's:
    # on a shared address one success would otherwise reset the budget an attacker is
    # burning through from the same network.
    await rl.clear_hits(session, rl.LOGIN, account)
    token = await create_token(session, user)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, token.token)
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    code: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    # ``code`` comes from the invite link the admin panel builds, so someone following
    # it only has to pick a username and password.
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "needs_code": await signup_requires_code(session),
            "signup_code": code.strip(),
        },
    )


def _password_error_message(exc: InvalidPasswordError) -> str:
    """The user-facing German text for a rejected password.

    Shared by registration and reset so the two paths cannot drift apart.
    """
    if exc.reason == "too_short":
        return f"Dein Passwort muss mindestens {PASSWORD_MIN_LENGTH} Zeichen lang sein."
    return "Dein Passwort ist zu lang – bitte höchstens 72 Zeichen."


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    signup_code: str = Form(default=""),
    session: AsyncSession = Depends(get_session),
):
    # Unlike login, this counts every attempt rather than only failures: creating
    # accounts in bulk to farm free credits is the abuse here, and each *success* is
    # what does the damage.
    ip = rl.ip_key(client_ip(request))
    await rl.enforce(session, rl.SIGNUP, ip)

    # Closing signup is the only thing that stops someone creating accounts in bulk to
    # farm free credits; the per-user and global credit limits only cap the damage.
    needs_code = await signup_requires_code(session)

    def _reject(message: str, code: int, *, needs: bool = needs_code) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": message,
                "needs_code": needs,
                "signup_code": signup_code.strip(),
                # Echo back what they typed so a rejected form is a correction, not a
                # blank slate they have to fill in again.
                "username": username.strip(),
                "email": email.strip(),
            },
            status_code=code,
        )

    # Cheap validation first: redeeming a code burns one of its seats, and a rejected
    # form must not cost the invite a seat the admin has to make up for.
    username = username.strip()
    if not username or not password or not email.strip():
        return _reject(
            "Benutzername, E-Mail-Adresse und Passwort sind erforderlich.",
            status.HTTP_400_BAD_REQUEST,
        )
    try:
        normalized_email = normalize_email(email)
    except InvalidEmailError:
        return _reject(
            "Bitte gib eine gültige E-Mail-Adresse ein.", status.HTTP_400_BAD_REQUEST
        )
    try:
        validate_password(password)
    except InvalidPasswordError as exc:
        return _reject(_password_error_message(exc), status.HTTP_400_BAD_REQUEST)

    if not await signup_allowed(session, signup_code):
        return _reject(
            "Ungültiger oder bereits aufgebrauchter Einladungscode.",
            status.HTTP_403_FORBIDDEN,
            needs=True,
        )

    try:
        user = await create_user(session, username, normalized_email, password)
    except (UsernameTakenError, EmailTakenError) as exc:
        # The seat was already taken from the code above; hand it back, or an invite
        # for 20 people would run out early on typos and retries.
        await refund_code(session, signup_code)
        message = (
            "Dieser Benutzername ist bereits vergeben."
            if isinstance(exc, UsernameTakenError)
            else "Für diese E-Mail-Adresse existiert bereits ein Konto."
        )
        return _reject(message, status.HTTP_409_CONFLICT)

    await rl.record_hit(session, rl.SIGNUP, ip)
    await _send_verification(session, user)
    token = await create_token(session, user)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, token.token)
    return response


# --- Email verification ---------------------------------------------------------

# Lower bound between two verification mails for one account. Stops a stuck client (or
# an impatient finger on the resend button) from turning the app into a mail relay
# aimed at someone else's inbox.
RESEND_INTERVAL = timedelta(seconds=60)


async def _send_verification(session: AsyncSession, user: User) -> None:
    """Issue a fresh verification token and mail it.

    Old tokens are dropped first so only the most recent link works — otherwise every
    resend leaves another live credential in another inbox copy.
    """
    await delete_user_tokens(session, user, VERIFY_TOKEN)
    token = await create_token(session, user, kind=VERIFY_TOKEN)
    await send_verification_email(user.email, user.username, token.token)


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(
    request: Request,
    token: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    user = await get_user_by_token(session, token, kind=VERIFY_TOKEN) if token else None
    if user is None:
        # Expired or already used. Not an error worth dwelling on — the page's job is
        # to offer a new mail, which is why it carries its own resend form.
        return templates.TemplateResponse(
            request=request,
            name="verify_result.html",
            context={"ok": False},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    await mark_email_verified(session, user)
    return templates.TemplateResponse(
        request=request, name="verify_result.html", context={"ok": True}
    )


@router.get("/verify-email/required", response_class=HTMLResponse)
async def verify_required(
    request: Request,
    user: Optional[User] = Depends(resolve_user),
) -> HTMLResponse:
    """The block page an unverified account lands on once its grace period lapses."""
    if user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if is_email_verified(user):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request, name="verify_required.html", context={"email": user.email}
    )


@router.post("/verify-email/resend")
async def resend_verification(
    request: Request,
    user: Optional[User] = Depends(resolve_user),
    session: AsyncSession = Depends(get_session),
):
    # Reachable while locked out — see core.deps. Without that exemption the grace
    # period would be a one-way door for anyone whose first mail never arrived.
    if user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    if is_email_verified(user):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    last_sent = await latest_token_created_at(session, user, VERIFY_TOKEN)
    throttled = (
        last_sent is not None
        and datetime.now(timezone.utc) - last_sent < RESEND_INTERVAL
    )
    if not throttled:
        await _send_verification(session, user)
    return templates.TemplateResponse(
        request=request,
        name="verify_required.html",
        context={
            "email": user.email,
            "sent": not throttled,
            "throttled": throttled,
        },
    )


# --- Password reset -------------------------------------------------------------

# Shown whether or not the address exists. Confirming which addresses have accounts
# would turn this form into a membership oracle for anyone who cares to ask.
_RESET_SENT_MESSAGE = (
    "Falls ein Konto mit dieser E-Mail-Adresse existiert, haben wir einen Link zum "
    "Zurücksetzen verschickt. Schau auch im Spam-Ordner nach."
)


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request, name="forgot_password.html", context={}
    )


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(
    request: Request,
    email: str = Form(...),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    # Per IP and per address: this endpoint sends mail to an address the caller
    # chooses, which makes it usable to flood someone else's inbox.
    ip = rl.ip_key(client_ip(request))
    await rl.enforce(session, rl.FORGOT_PASSWORD, ip, rl.account_key(email))
    await rl.record_hit(session, rl.FORGOT_PASSWORD, ip)

    try:
        normalized_email = normalize_email(email)
    except InvalidEmailError:
        # Same confirmation as a valid unknown address: a distinct "malformed" reply
        # is harmless on its own, but it invites probing the two responses apart.
        normalized_email = None

    if normalized_email is not None:
        await rl.record_hit(session, rl.FORGOT_PASSWORD, rl.account_key(normalized_email))
        user = await get_user_by_email(session, normalized_email)
        if user is not None:
            last_sent = await latest_token_created_at(session, user, RESET_TOKEN)
            if last_sent is None or datetime.now(timezone.utc) - last_sent >= RESEND_INTERVAL:
                await delete_user_tokens(session, user, RESET_TOKEN)
                token = await create_token(session, user, kind=RESET_TOKEN)
                await send_password_reset_email(user.email, user.username, token.token)

    return templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
        context={"message": _RESET_SENT_MESSAGE},
    )


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    user = await get_user_by_token(session, token, kind=RESET_TOKEN) if token else None
    return templates.TemplateResponse(
        request=request,
        name="reset_password.html",
        context={"token": token, "valid": user is not None},
        status_code=status.HTTP_200_OK if user else status.HTTP_400_BAD_REQUEST,
    )


@router.post("/reset-password")
async def submit_reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    def _reject(message: str = "", *, valid: bool = True) -> HTMLResponse:
        context = {"token": token, "valid": valid}
        if message:
            context["error"] = message
        return templates.TemplateResponse(
            request=request,
            name="reset_password.html",
            context=context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = await get_user_by_token(session, token, kind=RESET_TOKEN) if token else None
    if user is None:
        return _reject(valid=False)
    if not password:
        return _reject("Bitte gib ein neues Passwort ein.")
    try:
        validate_password(password)
    except InvalidPasswordError as exc:
        return _reject(_password_error_message(exc))

    await reset_password(session, user, password)
    # Every token is gone now, including this request's own — so hand out a fresh
    # session rather than bouncing the user back to the login form.
    new_token = await create_token(session, user)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, new_token.token)
    return response


@router.post("/logout")
async def logout(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await delete_token(session, token)
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.session_cookie_name)
    return response
