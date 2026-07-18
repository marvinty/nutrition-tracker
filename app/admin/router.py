from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.admin.deps import resolve_admin
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
)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.filters["localtime"] = lambda dt: to_local(dt).strftime("%H:%M")
templates.env.filters["de_date"] = lambda dt: format_day_month(
    to_local(dt).date(), with_year=True
)
router = APIRouter(prefix="/admin", tags=["admin"])

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
    admin = await authenticate_admin(session, username.strip(), password)
    if admin is None:
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={"error": "Benutzername oder Passwort ist ungültig."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
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
            "users": users,
        },
    )
