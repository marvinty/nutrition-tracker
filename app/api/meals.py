from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.schemas.meal import MealCreate, MealRead
from app.services.meal_service import create_meal, list_meals

router = APIRouter(prefix="/meals", tags=["meals"])


@router.post("", response_model=MealRead, status_code=201)
async def log_meal(
    body: MealCreate,
    session: AsyncSession = Depends(get_session),
) -> MealRead:
    meal = await create_meal(session, body)
    return meal


@router.get("", response_model=list[MealRead])
async def get_meals(
    user_id: str = Query(default="default"),
    filter_date: Optional[date] = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[MealRead]:
    return await list_meals(session, user_id=user_id, filter_date=filter_date)
