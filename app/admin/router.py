from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.admin.deps import resolve_admin
from app.core.csrf import register_csrf_field
from app.core.client_ip import client_ip
from app.core.config import settings
from app.core.dates_de import format_day_month
from app.core.time import to_local
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.services.admin_service import (
    authenticate_admin,
    create_admin_token,
    delete_admin_token,
    list_users_with_stats,
    set_user_tier,
)
from app.services import rate_limit_service as rl
from app.services.settings_service import is_signup_closed, set_signup_closed
from app.services.signup_code_service import create_code, list_codes, revoke_code

# Admin templates first, plus the dashboard templates for the shared _wordmark.html
# partial — the same two-directory arrangement auth and landing already use.
_dashboard_templates = Path(__file__).parent.parent / "dashboard" / "templates"
templates = register_csrf_field(
    Jinja2Templates(
        directory=[str(Path(__file__).parent / "templates"), str(_dashboard_templates)]
    )
)
templates.env.filters["localtime"] = lambda dt: to_local(dt).strftime("%H:%M")
templates.env.filters["de_date"] = lambda dt: format_day_month(
    to_local(dt).date(), with_year=True
)
router = APIRouter(prefix="/admin", tags=["admin"])

# German labels for the statuses computed in signup_code_service.
CODE_STATUS_LABELS = {
    "active": "aktiv",
    "used_up": "aufgebraucht",
    "expired": "abgelaufen",
    "revoked": "deaktiviert",
}

COOKIE_MAX_AGE = settings.admin_session_ttl_days * 24 * 60 * 60


def _set_admin_cookie(response: RedirectResponse, token: str) -> None:
    response.set_cookie(
        key=settings.admin_session_cookie_name,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="strict",  # stricter than the user session: no external entry points
        secure=settings.cookie_secure,
    )


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="admin_login.html", context={})


@router.post("/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    # The most valuable target in the app, and its password comes from an env var that
    # ships with "change-me" in .env.example — so this one is throttled hardest.
    ip = rl.ip_key(client_ip(request))
    account = rl.account_key(username)
    await rl.enforce(session, rl.ADMIN_LOGIN, ip, account)

    admin = await authenticate_admin(session, username.strip(), password)
    if admin is None:
        await rl.record_failure(session, rl.ADMIN_LOGIN, ip, account)
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={"error": "Benutzername oder Passwort ist ungültig."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    await rl.clear_hits(session, rl.ADMIN_LOGIN, account)
    token = await create_admin_token(session, admin)
    response = RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)
    _set_admin_cookie(response, token.token)
    return response


@router.post("/logout")
async def admin_logout(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    token = request.cookies.get(settings.admin_session_cookie_name)
    if token:
        await delete_admin_token(session, token)
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.admin_session_cookie_name)
    return response


@router.get("")
async def admin_index():
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/users")
async def admin_users(
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin: Optional[AdminUser] = Depends(resolve_admin),
):
    if admin is None:
        return RedirectResponse(url="/admin/login", status_code=303)
    users = await list_users_with_stats(session)
    return templates.TemplateResponse(
        request=request,
        name="admin_users.html",
        context={
            "admin_name": admin.username,
            "active_page": "users",
            "users": users,
            "tiers": list(settings.tier_daily_credits),
        },
    )


@router.post("/users/{username}/tier")
async def admin_set_user_tier(
    username: str,
    tier: str = Form(...),
    session: AsyncSession = Depends(get_session),
    admin: Optional[AdminUser] = Depends(resolve_admin),
):
    if admin is None:
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        await set_user_tier(session, username, tier)
    except ValueError:
        # Only reachable by posting past the <select>, same as admin_create_invite.
        pass
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/invites")
async def admin_invites(
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin: Optional[AdminUser] = Depends(resolve_admin),
):
    if admin is None:
        return RedirectResponse(url="/admin/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="admin_invites.html",
        context={
            "admin_name": admin.username,
            "active_page": "invites",
            "codes": await list_codes(session),
            "status_labels": CODE_STATUS_LABELS,
            "signup_closed": await is_signup_closed(session),
            "env_code_set": bool(settings.signup_code),
            # Invite links must point at the public host, not at whatever the admin
            # typed, so they still work when pasted into a chat.
            "base_url": str(request.base_url).rstrip("/"),
        },
    )


@router.post("/invites")
async def admin_create_invite(
    request: Request,
    max_uses: int = Form(...),
    label: str = Form(default=""),
    valid_days: str = Form(default=""),
    session: AsyncSession = Depends(get_session),
    admin: Optional[AdminUser] = Depends(resolve_admin),
):
    if admin is None:
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        days = int(valid_days) if valid_days.strip() else None
        await create_code(
            session,
            max_uses=max_uses,
            label=label,
            valid_days=days,
            created_by=admin.username,
        )
    except ValueError:
        # Bad input only ever comes from bypassing the form's own min/type checks, so a
        # plain redirect back to the page is enough — no error state to design for.
        pass
    return RedirectResponse(url="/admin/invites", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/invites/{code_id}/revoke")
async def admin_revoke_invite(
    code_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Optional[AdminUser] = Depends(resolve_admin),
):
    if admin is None:
        return RedirectResponse(url="/admin/login", status_code=303)
    await revoke_code(session, code_id)
    return RedirectResponse(url="/admin/invites", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/invites/signup-toggle")
async def admin_toggle_signup(
    closed: str = Form(default=""),
    session: AsyncSession = Depends(get_session),
    admin: Optional[AdminUser] = Depends(resolve_admin),
):
    if admin is None:
        return RedirectResponse(url="/admin/login", status_code=303)
    await set_signup_closed(session, closed == "1")
    return RedirectResponse(url="/admin/invites", status_code=status.HTTP_303_SEE_OTHER)
