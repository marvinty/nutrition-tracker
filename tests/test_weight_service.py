"""Tests for the weigh-in service: upsert/list/delete and the page assembly.

Like the other modules these exercise the service layer directly against an
in-memory SQLite database (no HTTP/auth stack). Config requires an API key at
import time, so dummy env vars are set before importing app modules.

The maths itself is covered in test_weight_analysis.py; what is checked here is the
storage contract (one row per day, user isolation) and that the two windows are
wired up the way ``get_weight_page_data`` claims.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.macro_goal import MacroGoal
from app.models.meal import Meal
from app.models.weight_entry import WeightEntry
from app.services.weight_service import (
    delete_entry,
    get_entry,
    get_weight_page_data,
    list_entries,
    upsert_entry,
)

TODAY = date(2026, 8, 1)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _day(offset: int) -> date:
    """``offset`` days before today."""
    return TODAY - timedelta(days=offset)


async def _seed(session, user: str, *, days: int = 28, kg: float = 80.0,
                calories: float = 2400.0, meal_days: int = 28) -> None:
    """Weigh-ins and meals over the last ``days`` days, ending yesterday."""
    for i in range(1, days + 1):
        session.add(WeightEntry(user_id=user, day=_day(i), weight_kg=kg))
    for i in range(1, meal_days + 1):
        # Stored as a tz-aware UTC timestamp at midday, so the local-day bucketing
        # in get_daily_series lands on the intended date regardless of DST.
        ts = datetime.combine(_day(i), datetime.min.time()).replace(
            hour=12, tzinfo=timezone.utc
        )
        session.add(
            Meal(user_id=user, description="Test", calories=calories, timestamp=ts)
        )
    await session.commit()


# ------------------------------------------------------------------ storage

@pytest.mark.asyncio
async def test_upsert_creates_then_replaces_the_same_day(session):
    await upsert_entry(session, "tester", TODAY, 80.4)
    updated = await upsert_entry(session, "tester", TODAY, 79.9)
    assert updated.weight_kg == 79.9

    rows = (await session.execute(select(WeightEntry))).scalars().all()
    assert len(rows) == 1  # one weigh-in per day, enforced by the unique constraint


@pytest.mark.asyncio
async def test_upsert_rounds_to_100g(session):
    entry = await upsert_entry(session, "tester", TODAY, 80.4444)
    assert entry.weight_kg == 80.4


@pytest.mark.asyncio
async def test_user_isolation(session):
    await upsert_entry(session, "alice", TODAY, 80.0)
    assert await get_entry(session, "bob", TODAY) is None
    assert await list_entries(session, "bob", _day(30), TODAY) == []
    # bob cannot delete alice's weigh-in by guessing the date
    assert await delete_entry(session, "bob", TODAY) is False
    assert await get_entry(session, "alice", TODAY) is not None


@pytest.mark.asyncio
async def test_delete_entry(session):
    await upsert_entry(session, "tester", TODAY, 80.0)
    assert await delete_entry(session, "tester", TODAY) is True
    assert await delete_entry(session, "tester", TODAY) is False


@pytest.mark.asyncio
async def test_list_entries_respects_bounds_and_sorts_ascending(session):
    for offset in (40, 10, 2, 0):
        await upsert_entry(session, "tester", _day(offset), 80.0 + offset)
    entries = await list_entries(session, "tester", _day(11), _day(1))
    assert [e.day for e in entries] == [_day(10), _day(2)]


# --------------------------------------------------------------- page data

@pytest.mark.asyncio
async def test_page_data_empty_state(session):
    view = await get_weight_page_data(session, "tester", None, TODAY)
    assert view["has_data"] is False
    assert view["blocked"] == "no_entries"
    assert view["estimate"] is None


@pytest.mark.asyncio
async def test_page_data_estimates_from_weight_and_meals(session):
    await _seed(session, "tester")
    goal = MacroGoal(user_id="tester", calories=2200, weekly_change_kg=0.3)
    view = await get_weight_page_data(session, "tester", goal, TODAY)

    assert view["blocked"] is None
    # Weight held exactly, so expenditure equals the logged intake.
    assert view["estimate"]["tdee"] == 2400
    assert view["estimate"]["suggested"] == 2750  # 2400 + 0.3*7700/7 = 2730 → nearest 50
    assert view["estimate"]["delta_to_goal"] == 550
    assert view["estimate"]["goal_calories"] == 2200
    # The intake window is the *trend* window, not the fetched 28 days: the first
    # smoothed point needs two weigh-ins behind it, so the trend starts a day later,
    # and it ends yesterday because today's meals are excluded.
    assert view["intake"]["days_total"] == view["trend"]["span_days"] + 1 == 26
    assert view["intake"]["days_logged"] == 26
    assert view["intake"]["coverage_pct"] == 100


@pytest.mark.asyncio
async def test_page_data_without_a_goal_has_no_suggestion(session):
    await _seed(session, "tester")
    view = await get_weight_page_data(session, "tester", None, TODAY)
    assert view["estimate"]["tdee"] == 2400
    assert view["estimate"]["suggested"] is None


@pytest.mark.asyncio
async def test_page_data_null_rate_differs_from_zero_rate(session):
    await _seed(session, "tester")
    no_rate = MacroGoal(user_id="tester", weekly_change_kg=None)
    hold = MacroGoal(user_id="tester", weekly_change_kg=0.0)

    assert (await get_weight_page_data(session, "tester", no_rate, TODAY))["estimate"][
        "suggested"
    ] is None
    # 0 means "halten" and must produce a real number, not be swallowed as falsy.
    assert (await get_weight_page_data(session, "tester", hold, TODAY))["estimate"][
        "suggested"
    ] == 2400


@pytest.mark.asyncio
async def test_page_data_blocks_when_meals_are_missing(session):
    await _seed(session, "tester", meal_days=20)  # 20 of 28 days = 71% < 80%
    view = await get_weight_page_data(session, "tester", None, TODAY)
    assert view["blocked"] == "intake_gaps"
    assert view["estimate"] is None


@pytest.mark.asyncio
async def test_page_data_ignores_todays_meals(session):
    """Today is half-logged, so it must not enter the intake average."""
    await _seed(session, "tester")
    view_before = await get_weight_page_data(session, "tester", None, TODAY)
    ts = datetime.combine(TODAY, datetime.min.time()).replace(
        hour=12, tzinfo=timezone.utc
    )
    session.add(Meal(user_id="tester", description="Snack", calories=200, timestamp=ts))
    await session.commit()
    view_after = await get_weight_page_data(session, "tester", None, TODAY)
    assert view_after["estimate"] == view_before["estimate"]


@pytest.mark.asyncio
async def test_deleting_entries_withdraws_the_estimate(session):
    await _seed(session, "tester")
    assert (await get_weight_page_data(session, "tester", None, TODAY))["estimate"]
    # Drop back below the minimum number of weigh-ins; the estimate must disappear
    # rather than go stale, since everything is recomputed per request.
    for i in range(1, 26):
        await delete_entry(session, "tester", _day(i))
    view = await get_weight_page_data(session, "tester", None, TODAY)
    assert view["estimate"] is None
    assert view["blocked"] == "too_few_entries"


@pytest.mark.asyncio
async def test_page_data_is_scoped_to_the_caller(session):
    await _seed(session, "alice")
    view = await get_weight_page_data(session, "bob", None, TODAY)
    assert view["has_data"] is False
