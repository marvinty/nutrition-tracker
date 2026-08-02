"""Weigh-in storage and the assembly of the /weight page.

The maths lives next door in ``weight_analysis`` and is pure; this module is the
only part that touches the database. ``get_weight_page_data`` is the seam: it does
the two queries, decides which windows to use, and hands everything to
``build_weight_view``. That assembly belongs here rather than in the router — the
routers in this app hold no business logic.
"""

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.macro_goal import MacroGoal
from app.models.weight_entry import WeightEntry
from app.services.meal_service import get_daily_series
from app.services.weight_analysis import CHART_DAYS, TREND_DAYS, build_weight_view

MIN_WEIGHT_KG = 20.0
MAX_WEIGHT_KG = 400.0


async def list_entries(
    session: AsyncSession, user_id: str, start: date, end: date
) -> list[WeightEntry]:
    """Weigh-ins in ``[start, end]``, ascending."""
    result = await session.execute(
        select(WeightEntry)
        .where(WeightEntry.user_id == user_id)
        .where(WeightEntry.day >= start, WeightEntry.day <= end)
        .order_by(WeightEntry.day)
    )
    return list(result.scalars().all())


async def get_entry(
    session: AsyncSession, user_id: str, day: date
) -> Optional[WeightEntry]:
    result = await session.execute(
        select(WeightEntry).where(
            WeightEntry.user_id == user_id, WeightEntry.day == day
        )
    )
    return result.scalar_one_or_none()


async def upsert_entry(
    session: AsyncSession, user_id: str, day: date, weight_kg: float
) -> WeightEntry:
    """Record ``day``'s weigh-in, replacing an existing one for that day.

    Select-then-write, the only upsert idiom in this codebase (see
    ``goal_service.upsert_goal`` and ``usage_service._reserve``); the unique
    constraint is the backstop for the two-tabs race, which a single uvicorn worker
    on SQLite makes vanishingly unlikely anyway.

    Rounded to 100 g: finer precision is scale noise, and stray decimals make the
    list ugly.
    """
    weight_kg = round(weight_kg, 1)
    entry = await get_entry(session, user_id, day)
    if entry is None:
        entry = WeightEntry(user_id=user_id, day=day, weight_kg=weight_kg)
        session.add(entry)
    else:
        entry.weight_kg = weight_kg
    await session.commit()
    await session.refresh(entry)
    return entry


async def delete_entry(session: AsyncSession, user_id: str, day: date) -> bool:
    """Delete a weigh-in by day. Keyed on the day rather than an id: a weigh-in has
    no identity beyond its date, and it matches the unique key."""
    entry = await get_entry(session, user_id, day)
    if entry is None:
        return False
    await session.delete(entry)
    await session.commit()
    return True


async def get_weight_page_data(
    session: AsyncSession,
    user_id: str,
    goal: Optional[MacroGoal],
    today: date,
) -> dict:
    """Everything /weight renders, display-ready.

    Two queries: the weigh-ins for the chart window, and — only if there are any —
    the daily meal totals for the trend window, reusing ``get_daily_series`` rather
    than adding a second way to total a day.

    The intake side stops at *yesterday* — today's meals are only half logged and
    would drag the average down, inflating the estimate. The weight side runs to
    today, because a weigh-in is complete when it is taken; see ``build_weight_view``
    for why that asymmetry is worth its one-day offset.
    """
    chart_start = today - timedelta(days=CHART_DAYS - 1)
    entries = await list_entries(session, user_id, chart_start, today)

    intake_end = today - timedelta(days=1)
    trend_start = today - timedelta(days=TREND_DAYS - 1)
    intake_series: list[dict] = []
    if entries:
        intake_series = await get_daily_series(
            session, user_id=user_id, start=trend_start, end=intake_end
        )

    return build_weight_view(
        [(e.day, e.weight_kg) for e in entries],
        intake_series,
        trend_start=trend_start,
        trend_end=today,
        intake_end=intake_end,
        # 0.0 is a stated rate ("halten"); only a missing goal or a NULL column
        # means "not stated". Never coerce one into the other.
        desired_rate_kg_week=goal.weekly_change_kg if goal is not None else None,
        goal_calories=goal.calories if goal is not None else None,
    )
