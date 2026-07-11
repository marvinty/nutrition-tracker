"""Tests for the voice usage limiter service.

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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import time as core_time
from app.models.base import Base
from app.models.voice_usage import VoiceUsage  # noqa: F401 — register with Base.metadata
from app.services.usage_service import check_and_increment_voice


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
async def test_increments_up_to_limit(session):
    for expected in (1, 2, 3):
        assert await check_and_increment_voice(session, "alice", limit=3) == expected


@pytest.mark.asyncio
async def test_raises_429_at_limit(session):
    for _ in range(2):
        await check_and_increment_voice(session, "alice", limit=2)
    with pytest.raises(HTTPException) as exc:
        await check_and_increment_voice(session, "alice", limit=2)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_counter_resets_on_new_day(session, monkeypatch):
    day1 = core_time.today_local()
    for _ in range(2):
        await check_and_increment_voice(session, "alice", limit=2)

    # Advance the "local day" by one; the quota should start fresh.
    # usage_service imports today_local by name, so patch it in that module.
    monkeypatch.setattr(
        "app.services.usage_service.today_local", lambda: day1 + timedelta(days=1)
    )
    assert await check_and_increment_voice(session, "alice", limit=2) == 1


@pytest.mark.asyncio
async def test_user_isolation(session):
    await check_and_increment_voice(session, "alice", limit=1)
    # bob has his own counter and is unaffected by alice hitting her limit.
    assert await check_and_increment_voice(session, "bob", limit=1) == 1
    with pytest.raises(HTTPException):
        await check_and_increment_voice(session, "alice", limit=1)
