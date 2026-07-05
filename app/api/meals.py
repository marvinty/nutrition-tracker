from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.providers import get_provider
from app.providers.base import LLMProvider
from app.schemas.meal import MealCreate, MealInput, MealRead, TextMealCreate
from app.services.meal_service import create_meal, list_meals

router = APIRouter(prefix="/meals", tags=["meals"])


@router.post("", response_model=MealRead, status_code=201)
async def log_meal(
    body: MealInput,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> MealRead:
    meal = await create_meal(
        session, MealCreate(user_id=user.username, **body.model_dump())
    )
    return meal


@router.post("/text", response_model=MealRead, status_code=201)
async def log_meal_from_text(
    body: TextMealCreate,
    session: AsyncSession = Depends(get_session),
    provider: LLMProvider = Depends(get_provider),
    user: User = Depends(get_current_user),
) -> MealRead:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")

    try:
        nutrition = await provider.extract_nutrition(body.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {exc}") from exc

    return await create_meal(
        session,
        MealCreate(
            user_id=user.username,
            description=nutrition.description,
            calories=nutrition.calories,
            protein=nutrition.protein,
            carbs=nutrition.carbs,
            fat=nutrition.fat,
        ),
    )


@router.get("", response_model=list[MealRead])
async def get_meals(
    filter_date: Optional[date] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[MealRead]:
    return await list_meals(session, user_id=user.username, filter_date=filter_date)
