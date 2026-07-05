from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.router import api_router
from app.auth.router import router as auth_router
from app.dashboard.router import router as dashboard_router
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Nutrition Tracker API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(dashboard_router)
