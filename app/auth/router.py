from pathlib import Path
from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_session
from app.services.auth_service import (
    UsernameTakenError,
    authenticate_user,
    create_token,
    create_user,
    delete_token,
)
from app.services.signup_code_service import (
    refund_code,
    signup_allowed,
    signup_requires_code,
)

# Search auth templates first, plus the dashboard templates for the shared base.html.
_dashboard_templates = Path(__file__).parent.parent / "dashboard" / "templates"
templates = Jinja2Templates(
    directory=[str(Path(__file__).parent / "templates"), str(_dashboard_templates)]
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
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    user = await authenticate_user(session, username.strip(), password)
    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Benutzername oder Passwort ist ungültig."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
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


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    signup_code: str = Form(default=""),
    session: AsyncSession = Depends(get_session),
):
    # Closing signup is the only thing that stops someone creating accounts in bulk to
    # farm free credits; the per-user and global credit limits only cap the damage.
    needs_code = await signup_requires_code(session)

    # Cheap validation first: redeeming a code burns one of its seats, and a rejected
    # form must not cost the invite a seat the admin has to make up for.
    username = username.strip()
    if not username or not password:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": "Benutzername und Passwort sind erforderlich.",
                "needs_code": needs_code,
                "signup_code": signup_code.strip(),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not await signup_allowed(session, signup_code):
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": "Ungültiger oder bereits aufgebrauchter Einladungscode.",
                "needs_code": True,
                "signup_code": signup_code.strip(),
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )

    try:
        user = await create_user(session, username, password)
    except UsernameTakenError:
        # The seat was already taken from the code above; hand it back, or an invite
        # for 20 people would run out early on typos and retries.
        await refund_code(session, signup_code)
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": "Dieser Benutzername ist bereits vergeben.",
                "needs_code": needs_code,
                "signup_code": signup_code.strip(),
            },
            status_code=status.HTTP_409_CONFLICT,
        )
    token = await create_token(session, user)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, token.token)
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
