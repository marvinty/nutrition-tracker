from datetime import date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.time import day_bounds, to_local
from app.models.meal import Meal
from app.schemas.meal import MealCreate


async def create_meal(session: AsyncSession, data: MealCreate) -> Meal:
    fields = data.model_dump(exclude={"timestamp"})
    if data.timestamp is not None:
        fields["timestamp"] = data.timestamp
    meal = Meal(**fields)
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
        start, end = day_bounds(filter_date)
        stmt = stmt.where(Meal.timestamp >= start, Meal.timestamp < end)
    result = await session.execute(stmt)
    return list(result.scalars().all())


def _empty_totals() -> dict:
    return {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "meal_count": 0}


def _accumulate(totals: dict, meal: Meal) -> None:
    totals["calories"] += meal.calories or 0
    totals["protein"] += meal.protein or 0
    totals["carbs"] += meal.carbs or 0
    totals["fat"] += meal.fat or 0
    totals["meal_count"] += 1


def _round_totals(totals: dict) -> dict:
    return {
        "calories": round(totals["calories"], 1),
        "protein": round(totals["protein"], 1),
        "carbs": round(totals["carbs"], 1),
        "fat": round(totals["fat"], 1),
        "meal_count": totals["meal_count"],
    }


async def get_daily_totals(session: AsyncSession, user_id: str, for_date: date) -> dict:
    meals = await list_meals(session, user_id=user_id, filter_date=for_date)
    totals = _empty_totals()
    for meal in meals:
        _accumulate(totals, meal)
    return _round_totals(totals)


async def get_daily_series(
    session: AsyncSession, user_id: str, start: date, end: date
) -> list[dict]:
    """Per-day totals for every local calendar day in [start, end] (inclusive).

    Fetches all meals in the range with a single query and buckets them in Python by
    their local calendar date, so empty days still appear with zeroed totals.
    """
    range_start, _ = day_bounds(start)
    _, range_end = day_bounds(end)
    stmt = (
        select(Meal)
        .where(Meal.user_id == user_id)
        .where(Meal.timestamp >= range_start, Meal.timestamp < range_end)
    )
    result = await session.execute(stmt)
    meals = list(result.scalars().all())

    buckets: dict[date, dict] = {}
    d = start
    while d <= end:
        buckets[d] = {"date": d, **_empty_totals()}
        d = date.fromordinal(d.toordinal() + 1)

    for meal in meals:
        day = to_local(meal.timestamp).date()
        if day in buckets:
            _accumulate(buckets[day], meal)

    return [{"date": day, **_round_totals(t)} for day, t in sorted(buckets.items())]


def get_period_summary(series: list[dict]) -> dict:
    """Totals and per-day averages across a daily series."""
    days = len(series) or 1
    total = _empty_totals()
    for entry in series:
        total["calories"] += entry["calories"]
        total["protein"] += entry["protein"]
        total["carbs"] += entry["carbs"]
        total["fat"] += entry["fat"]
        total["meal_count"] += entry["meal_count"]
    return {
        "total": _round_totals(total),
        "avg": {
            "calories": round(total["calories"] / days, 1),
            "protein": round(total["protein"] / days, 1),
            "carbs": round(total["carbs"] / days, 1),
            "fat": round(total["fat"] / days, 1),
        },
        "days": len(series),
    }
