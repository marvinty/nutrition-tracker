import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.admin.router import router as admin_router
from app.api.router import api_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.dashboard.router import router as dashboard_router
from app.db.init_db import init_db
from app.db.session import async_session_maker
from app.services.admin_service import ensure_bootstrap_admin

logger = logging.getLogger(__name__)


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
    async with async_session_maker() as session:
        await ensure_bootstrap_admin(session)
    yield


app = FastAPI(title="Nutrition Tracker API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
