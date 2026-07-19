import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.admin.router import router as admin_router
from app.api.router import api_router
from app.auth.router import router as auth_router
from app.auth.router import templates as auth_templates
from app.core.config import settings
from app.core.csrf import CSRFMiddleware
from app.core.deps import EmailVerificationRequired
from app.dashboard.router import router as dashboard_router
from app.db.init_db import init_db
from app.db.session import async_session_maker
from app.landing.router import router as landing_router
from app.services.admin_service import ensure_bootstrap_admin
from app.services.rate_limit_service import prune_expired

logger = logging.getLogger(__name__)

# Uvicorn configures only its own loggers; the root logger stays at WARNING, which
# silently swallowed every logger.info() in the app. Mail delivery in particular needs
# its happy path visible — otherwise a quiet log is ambiguous between "sent" and "never
# attempted", which is exactly the confusion this is meant to prevent.
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if not settings.signup_code:
        # Easy to miss when deploying, and the consequence is anyone being able to
        # create accounts and spend credits, so say it out loud on every boot.
        logger.warning(
            "SIGNUP_CODE is not set — registration is open to anyone. "
            "Set it in .env to close signup."
        )
    # Mail misconfiguration is silent by nature: registration still succeeds, the user
    # just never gets the link. Each of these is only visible at boot, so say it here
    # rather than leaving it to be discovered by a user who never received anything.
    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY is not set — verification and password-reset mails are "
            "only written to this log, not delivered. Note that .env is read at import "
            "time, so adding the key needs a restart, not just a reload."
        )
    elif "example.com" in settings.email_from:
        logger.warning(
            "EMAIL_FROM is still %s — Resend rejects any sender that is not on a "
            "domain you have verified, so every mail will fail.",
            settings.email_from,
        )
    if "localhost" in settings.public_base_url:
        logger.warning(
            "PUBLIC_BASE_URL is %s — links in outgoing mail will point at localhost "
            "and be unusable for anyone but you.",
            settings.public_base_url,
        )

    async with async_session_maker() as session:
        await ensure_bootstrap_admin(session)
        # Rows outside the window are meaningless; clearing them at boot is enough to
        # keep the table from growing across restarts without a scheduled job.
        await prune_expired(session)
    yield


app = FastAPI(title="MacroMic API", lifespan=lifespan)
app.add_middleware(CSRFMiddleware)

# Brand assets (wordmark, favicon). The first static files the app has had — every
# other stylesheet and icon is inlined in its template.
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)


@app.exception_handler(StarletteHTTPException)
async def _http_exception(request: Request, exc: StarletteHTTPException):
    """Render 429 as a page for form posts, keeping JSON everywhere else.

    The rate limiter guards HTML forms as well as the API, and FastAPI's default
    renders every HTTPException as JSON — which for someone who mistyped their password
    too often would mean a bare line of JSON instead of an explanation. Anything that
    is not this specific case is handed straight back to the default handler.
    """
    is_browser_form = not request.url.path.startswith("/api/")
    if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS and is_browser_form:
        return auth_templates.TemplateResponse(
            request=request,
            name="rate_limited.html",
            context={"detail": exc.detail},
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )
    return await http_exception_handler(request, exc)


@app.exception_handler(EmailVerificationRequired)
async def _email_verification_required(request: Request, exc: EmailVerificationRequired):
    """Send a locked account to the page that can unlock it.

    A browser gets a redirect; an API client gets 403 with a message, since following a
    redirect to an HTML page would only confuse it.
    """
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "E-Mail-Adresse ist noch nicht bestätigt."},
        )
    return RedirectResponse(
        url="/verify-email/required", status_code=status.HTTP_303_SEE_OTHER
    )


app.include_router(landing_router)
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
