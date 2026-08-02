"""Tests for the one-time schema/data migrations in ``init_db``.

Covers the token-total backfill (which seeds the lifetime counter from the AI logs
that survive at deploy time) and the ``macrogoal.weekly_change_kg`` column add. Like
the other modules this runs against an in-memory SQLite database, so the dummy env
vars are set before import.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sqlalchemy import text

from app.db.init_db import _add_goal_weekly_change_column, _backfill_token_totals
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


# ---------------------------------------------- macrogoal.weekly_change_kg


async def _macrogoal_columns(engine) -> list[str]:
    async with engine.begin() as conn:
        rows = await conn.execute(text("PRAGMA table_info(macrogoal)"))
        return [r[1] for r in rows]


@pytest_asyncio.fixture
async def legacy_engine():
    """An engine whose ``macrogoal`` predates the weekly_change_kg column.

    Built by hand rather than with ``create_all``: against a current schema the
    migration would only ever exercise its early return, which is the one path that
    cannot break a live deployment.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE macrogoal (
                    id INTEGER NOT NULL PRIMARY KEY,
                    user_id VARCHAR NOT NULL UNIQUE,
                    calories FLOAT, protein FLOAT, carbs FLOAT, fat FLOAT,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        await conn.execute(
            text("INSERT INTO macrogoal (user_id, calories) VALUES ('alice', 2500)")
        )
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_adds_weekly_change_column_to_a_legacy_macrogoal(legacy_engine):
    assert "weekly_change_kg" not in await _macrogoal_columns(legacy_engine)

    async with legacy_engine.begin() as conn:
        await _add_goal_weekly_change_column(conn)

    assert "weekly_change_kg" in await _macrogoal_columns(legacy_engine)

    # No backfill: an existing user never stated a target rate, and NULL is exactly
    # that. A default of 0 would claim they want to hold their weight.
    async with legacy_engine.begin() as conn:
        rows = await conn.execute(
            text("SELECT calories, weekly_change_kg FROM macrogoal WHERE user_id='alice'")
        )
        assert rows.first() == (2500.0, None)


@pytest.mark.asyncio
async def test_weekly_change_migration_is_idempotent(legacy_engine):
    for _ in range(2):
        async with legacy_engine.begin() as conn:
            await _add_goal_weekly_change_column(conn)
    columns = await _macrogoal_columns(legacy_engine)
    assert columns.count("weekly_change_kg") == 1


@pytest.mark.asyncio
async def test_weekly_change_migration_is_a_noop_on_a_fresh_schema(engine):
    async with engine.begin() as conn:
        await _add_goal_weekly_change_column(conn)
    assert "weekly_change_kg" in await _macrogoal_columns(engine)
