"""Tests for the macro-goal service: upsert/get of per-user targets and the
pure progress/adherence helpers.

Like test_recipes, these exercise the service layer directly with an in-memory
SQLite database (no HTTP/auth stack). Config requires an API key at import time,
so we set dummy env vars before importing app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.macro_goal import MacroGoal  # noqa: F401 — register with Base.metadata
from app.schemas.goal import GoalUpdate
from app.services.goal_service import (
    build_progress,
    get_goal,
    period_adherence,
    upsert_goal,
)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_goal_none_without_row(session):
    assert await get_goal(session, "nobody") is None


@pytest.mark.asyncio
async def test_upsert_creates_then_updates(session):
    goal = await upsert_goal(session, "tester", GoalUpdate(protein=180, calories=2500))
    assert goal.protein == 180 and goal.calories == 2500
    assert goal.carbs is None and goal.fat is None

    # PUT semantics: full replace — omitting a field clears it, changing one updates it.
    updated = await upsert_goal(session, "tester", GoalUpdate(protein=200))
    assert updated.protein == 200
    assert updated.calories is None  # cleared

    # Still a single row for the user.
    fetched = await get_goal(session, "tester")
    assert fetched.protein == 200


@pytest.mark.asyncio
async def test_user_isolation(session):
    await upsert_goal(session, "alice", GoalUpdate(protein=150))
    assert await get_goal(session, "bob") is None


def _goal(**kw):
    return MacroGoal(user_id="t", **kw)


def test_build_progress_basic():
    totals = {"calories": 1250, "protein": 90, "carbs": 100, "fat": 40}
    goal = _goal(calories=2500, protein=180)
    progress = build_progress(totals, goal)

    assert set(progress) == {"calories", "protein"}  # carbs/fat have no target
    assert progress["protein"]["percent"] == 50
    assert progress["protein"]["bar_pct"] == 50
    assert progress["protein"]["remaining"] == 90.0
    assert progress["protein"]["over"] is False


def test_build_progress_over_target_clamps_bar():
    goal = _goal(protein=100)
    progress = build_progress({"protein": 130}, goal)
    assert progress["protein"]["percent"] == 130
    assert progress["protein"]["bar_pct"] == 100  # clamped for the bar width
    assert progress["protein"]["over"] is True
    assert progress["protein"]["remaining"] == -30.0


def test_build_progress_no_goal_and_zero_target():
    assert build_progress({"protein": 50}, None) == {}
    # A target of 0 is treated as "no goal" and must not divide by zero.
    assert build_progress({"protein": 50}, _goal(protein=0)) == {}


def test_period_adherence_counts_logged_days_only():
    goal = _goal(protein=180)
    series = [
        {"protein": 200, "meal_count": 3},  # hit
        {"protein": 150, "meal_count": 2},  # logged, missed
        {"protein": 0, "meal_count": 0},    # no meals — ignored
        {"protein": 180, "meal_count": 1},  # exactly on target — hit
    ]
    result = period_adherence(series, goal)
    assert result == {"protein_hit": 2, "logged_days": 3, "protein_target": 180.0}


def test_period_adherence_none_without_protein_goal():
    series = [{"protein": 200, "meal_count": 1}]
    assert period_adherence(series, None) is None
    assert period_adherence(series, _goal(calories=2000)) is None
