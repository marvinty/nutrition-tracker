from pathlib import Path
from fastapi import APIRouter, Depends, Form, Request, status
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
            context={"error": "Invalid username or password."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    token = await create_token(session, user)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, token.token)
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="register.html", context={})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    username = username.strip()
    if not username or not password:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "Username and password are required."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        user = await create_user(session, username, password)
    except UsernameTakenError:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "Username is already taken."},
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
