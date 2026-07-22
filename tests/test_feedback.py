"""Tests for the feedback service: storing a message and listing it back.

Like the other test modules these exercise the service layer directly against an
in-memory SQLite database. Config requires an API key at import time, so dummy
env vars are set before importing app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.feedback import Feedback
from app.services.feedback_service import (
    CATEGORY_LABELS,
    create_feedback,
    list_feedback,
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
async def test_create_feedback_persists_the_row(session):
    entry = await create_feedback(session, "alice", "bug", "Der Zähler springt.")
    assert entry.id is not None
    assert entry.user_id == "alice"
    assert entry.category == "bug"
    assert entry.message == "Der Zähler springt."
    assert entry.created_at is not None  # server_default filled in on commit


@pytest.mark.asyncio
async def test_list_feedback_orders_newest_first(session):
    base = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    session.add_all(
        [
            Feedback(user_id="alice", category="idea", message="alt", created_at=base),
            Feedback(
                user_id="bob", category="bug", message="neu",
                created_at=base + timedelta(hours=2),
            ),
        ]
    )
    await session.commit()

    rows = await list_feedback(session)
    assert [r.message for r in rows] == ["neu", "alt"]
    assert len(await list_feedback(session, limit=1)) == 1


def test_category_labels_cover_the_form_choices():
    # The <select> in feedback.html and the router's validation both read these
    # keys, so the set is the contract.
    assert set(CATEGORY_LABELS) == {"bug", "idea", "other"}
