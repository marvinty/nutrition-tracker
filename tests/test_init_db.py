"""Tests for the one-time schema/data migrations in ``init_db``.

Only the token-total backfill is covered here; it seeds the lifetime counter from
the AI logs that survive at deploy time. Like the other modules this runs against
an in-memory SQLite database, so the dummy env vars are set before import.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.init_db import _backfill_token_totals
from app.models.ai_request_log import AiRequestLog
from app.models.base import Base
from app.models.user_token_total import UserTokenTotal


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


async def _totals(engine) -> dict[str, tuple[int, int]]:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        rows = (
            await s.execute(
                select(
                    UserTokenTotal.user_id,
                    UserTokenTotal.prompt_tokens,
                    UserTokenTotal.completion_tokens,
                )
            )
        ).all()
    return {r[0]: (r[1], r[2]) for r in rows}


def _log(**kw) -> AiRequestLog:
    defaults = dict(
        kind="llm_analyze", provider="claude", request_text="x", latency_ms=1,
        created_at=datetime.now(timezone.utc),
    )
    return AiRequestLog(**{**defaults, **kw})


@pytest.mark.asyncio
async def test_backfill_sums_existing_logs_per_user(engine):
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        s.add_all(
            [
                _log(user_id="alice", prompt_tokens=100, completion_tokens=30),
                _log(user_id="alice", prompt_tokens=50, completion_tokens=10),
                _log(user_id="bob", prompt_tokens=7, completion_tokens=2),
                # No tokens (transcribe/failure) and no user: excluded from the seed.
                _log(user_id="carol", prompt_tokens=None, completion_tokens=None),
                _log(user_id=None, prompt_tokens=9, completion_tokens=9),
            ]
        )
        await s.commit()

    async with engine.begin() as conn:
        await _backfill_token_totals(conn)

    assert await _totals(engine) == {"alice": (150, 40), "bob": (7, 2)}


@pytest.mark.asyncio
async def test_backfill_is_a_noop_when_counter_already_populated(engine):
    """Runs only on the first boot after the table exists — later restarts must
    not double-count on top of the live counter."""
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        s.add(_log(user_id="alice", prompt_tokens=100, completion_tokens=30))
        s.add(UserTokenTotal(user_id="alice", prompt_tokens=999, completion_tokens=999))
        await s.commit()

    async with engine.begin() as conn:
        await _backfill_token_totals(conn)

    assert await _totals(engine) == {"alice": (999, 999)}
