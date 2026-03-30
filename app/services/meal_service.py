from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.meal import Meal
from app.schemas.meal import MealCreate


async def create_meal(session: AsyncSession, data: MealCreate) -> Meal:
    meal = Meal(**data.model_dump())
    session.add(meal)
    await session.commit()
    await session.refresh(meal)
    return meal


async def list_meals(
    session: AsyncSession,
    user_id: str,
    filter_date: Optional[date] = None,
) -> list[Meal]:
    stmt = select(Meal).where(Meal.user_id == user_id).order_by(Meal.timestamp.desc())
    if filter_date:
        start = datetime(filter_date.year, filter_date.month, filter_date.day, tzinfo=timezone.utc)
        end = datetime(filter_date.year, filter_date.month, filter_date.day, 23, 59, 59, tzinfo=timezone.utc)
        stmt = stmt.where(Meal.timestamp.between(start, end))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_daily_totals(session: AsyncSession, user_id: str, for_date: date) -> dict:
    meals = await list_meals(session, user_id=user_id, filter_date=for_date)
    return {
        "calories": round(sum(m.calories or 0 for m in meals), 1),
        "protein": round(sum(m.protein or 0 for m in meals), 1),
        "carbs": round(sum(m.carbs or 0 for m in meals), 1),
        "fat": round(sum(m.fat or 0 for m in meals), 1),
        "meal_count": len(meals),
    }
