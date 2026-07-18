"""Tests for the AI credit limiter service.

Like test_goals, these exercise the service layer directly with an in-memory
SQLite database (no HTTP/auth stack). Config requires an API key at import time,
so we set dummy env vars before importing app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import timedelta

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import time as core_time
from app.models.base import Base
from app.models.ai_usage import AiUsage  # noqa: F401 — register with Base.metadata
from app.core.config import settings
from app.services.usage_service import (
    GLOBAL_KEY,
    consume_credits,
    get_credit_status,
    get_usage,
    limit_for,
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
async def test_accumulates_up_to_limit(session):
    for expected in (1, 2, 3):
        assert await consume_credits(session, "alice", cost=1, limit=3) == expected


@pytest.mark.asyncio
async def test_raises_429_at_limit(session):
    for _ in range(2):
        await consume_credits(session, "alice", cost=1, limit=2)
    with pytest.raises(HTTPException) as exc:
        await consume_credits(session, "alice", cost=1, limit=2)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_cost_is_weighted(session):
    # A voice call costs 3, so it eats three times the budget of a text call.
    assert await consume_credits(session, "alice", cost=3, limit=10) == 3
    assert await consume_credits(session, "alice", cost=1, limit=10) == 4


@pytest.mark.asyncio
async def test_rejects_action_that_would_overdraw(session):
    # 2 of 4 credits left is enough for text (1) but not for voice (3): the
    # expensive action is refused outright rather than pushing the total over.
    await consume_credits(session, "alice", cost=2, limit=4)
    with pytest.raises(HTTPException) as exc:
        await consume_credits(session, "alice", cost=3, limit=4)
    assert exc.value.status_code == 429
    # ...and the rejected call did not consume anything.
    assert await get_usage(session, "alice") == 2
    assert await consume_credits(session, "alice", cost=1, limit=4) == 3


@pytest.mark.asyncio
async def test_pro_tier_gets_a_bigger_budget(session):
    # The same spend that exhausts a free budget is fine against a pro one.
    await consume_credits(session, "alice", cost=20, limit=20)
    with pytest.raises(HTTPException):
        await consume_credits(session, "alice", cost=1, limit=20)
    assert await consume_credits(session, "alice", cost=1, limit=300) == 21


@pytest.mark.asyncio
async def test_counter_resets_on_new_day(session, monkeypatch):
    day1 = core_time.today_local()
    await consume_credits(session, "alice", cost=2, limit=2)

    # Advance the "local day" by one; the budget should start fresh.
    # usage_service imports today_local by name, so patch it in that module.
    monkeypatch.setattr(
        "app.services.usage_service.today_local", lambda: day1 + timedelta(days=1)
    )
    assert await consume_credits(session, "alice", cost=1, limit=2) == 1


@pytest.mark.asyncio
async def test_user_isolation(session):
    await consume_credits(session, "alice", cost=1, limit=1)
    # bob has his own budget and is unaffected by alice hitting her limit.
    assert await consume_credits(session, "bob", cost=1, limit=1) == 1
    with pytest.raises(HTTPException):
        await consume_credits(session, "alice", cost=1, limit=1)


@pytest.mark.asyncio
async def test_get_usage_defaults_to_zero(session):
    assert await get_usage(session, "newcomer") == 0


@pytest.mark.asyncio
async def test_global_ceiling_stops_users_who_are_under_their_own_limit(session):
    # Five users with plenty of personal budget each, but a shared ceiling of 4.
    for i in range(4):
        await consume_credits(session, f"user{i}", cost=1, limit=100, global_limit=4)
    with pytest.raises(HTTPException) as exc:
        await consume_credits(session, "user4", cost=1, limit=100, global_limit=4)
    assert exc.value.status_code == 429
    assert "Systemlimit" in exc.value.detail  # not the personal-limit wording
    assert await get_usage(session, GLOBAL_KEY) == 4


@pytest.mark.asyncio
async def test_global_counter_tracks_every_user(session):
    await consume_credits(session, "alice", cost=3, limit=100, global_limit=100)
    await consume_credits(session, "bob", cost=1, limit=100, global_limit=100)
    assert await get_usage(session, GLOBAL_KEY) == 4
    assert await get_usage(session, "alice") == 3


@pytest.mark.asyncio
async def test_rejection_by_user_limit_does_not_charge_the_global_counter(session):
    # Both counters move in one transaction, so alice hitting her own limit must not
    # quietly burn shared budget — otherwise one user could drain the ceiling with
    # requests that were all refused anyway.
    await consume_credits(session, "alice", cost=1, limit=1, global_limit=100)
    with pytest.raises(HTTPException):
        await consume_credits(session, "alice", cost=1, limit=1, global_limit=100)
    assert await get_usage(session, GLOBAL_KEY) == 1


@pytest.mark.asyncio
async def test_global_limit_is_optional(session):
    # Omitting it skips the ceiling entirely and writes no global row.
    await consume_credits(session, "alice", cost=1, limit=10)
    assert await get_usage(session, GLOBAL_KEY) == 0


def test_limit_for_falls_back_to_free(monkeypatch):
    monkeypatch.setattr(settings, "tier_daily_credits", {"free": 20, "pro": 300})
    assert limit_for("pro") == 300
    assert limit_for("free") == 20
    # A typo in the DB must not hand out an unlimited budget.
    assert limit_for("prooo") == 20


@pytest.mark.asyncio
async def test_credit_status_reports_remaining_budget(session, monkeypatch):
    monkeypatch.setattr(settings, "tier_daily_credits", {"free": 20, "pro": 300})
    monkeypatch.setattr(settings, "global_daily_credits", 500)
    await consume_credits(session, "alice", cost=3, limit=20, global_limit=500)

    status = await get_credit_status(session, "alice", "free")
    assert (status.used, status.limit, status.remaining) == (3, 20, 17)
    assert status.tier == "free"
    assert status.system_available is True


@pytest.mark.asyncio
async def test_credit_status_flags_the_ceiling_while_user_still_has_budget(
    session, monkeypatch
):
    # The case the flag exists for: bob's own budget looks untouched, but the shared
    # ceiling is spent, so the UI must say so instead of showing a full budget.
    monkeypatch.setattr(settings, "tier_daily_credits", {"free": 20, "pro": 300})
    monkeypatch.setattr(settings, "global_daily_credits", 2)
    await consume_credits(session, "alice", cost=2, limit=20, global_limit=2)

    status = await get_credit_status(session, "bob", "free")
    assert status.remaining == 20  # personally untouched
    assert status.system_available is False


@pytest.mark.asyncio
async def test_credit_status_remaining_never_goes_negative(session, monkeypatch):
    # A tier downgrade can leave someone above their new limit; the UI shows 0, not -5.
    monkeypatch.setattr(settings, "tier_daily_credits", {"free": 20, "pro": 300})
    monkeypatch.setattr(settings, "global_daily_credits", 500)
    await consume_credits(session, "alice", cost=25, limit=300, global_limit=500)

    status = await get_credit_status(session, "alice", "free")
    assert status.remaining == 0
