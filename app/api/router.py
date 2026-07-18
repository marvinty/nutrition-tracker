from fastapi import APIRouter
from app.api.meals import router as meals_router
from app.api.audio import router as audio_router
from app.api.recipes import router as recipes_router
from app.api.goals import router as goals_router
from app.api.usage import router as usage_router

api_router = APIRouter()
api_router.include_router(meals_router)
api_router.include_router(audio_router)
api_router.include_router(recipes_router)
api_router.include_router(goals_router)
api_router.include_router(usage_router)
