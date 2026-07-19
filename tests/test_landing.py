"""Tests for the public landing page at ``/``.

Like the other test modules these call into the app directly rather than through
the HTTP stack (the repo has no test client set up). Config requires an API key at
import time, so dummy env vars are set before importing app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.landing.router import landing
from app.models.base import Base
from app.models.app_setting import AppSetting  # noqa: F401 — register with Base.metadata
from app.services.settings_service import set_signup_closed


class _Request:
    """Stand-in for Request — the landing template needs no request context."""


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
async def test_anonymous_visitor_gets_the_landing_page(session):
    response = await landing(_Request(), user=None, session=session)

    assert response.status_code == 200
    body = response.body.decode()
    assert "Jetzt registrieren" in body
    assert 'href="/register"' in body
    assert 'href="/login"' in body


@pytest.mark.asyncio
async def test_invite_hint_appears_only_while_signup_is_closed(session):
    await set_signup_closed(session, True)
    closed = (await landing(_Request(), user=None, session=session)).body.decode()
    assert "Invite-Code" in closed

    # Reopening signup in the admin panel must take the hint off the landing page —
    # otherwise the CTA warns about a code nobody needs any more.
    await set_signup_closed(session, False)
    opened = (await landing(_Request(), user=None, session=session)).body.decode()
    assert "Invite-Code" not in opened


@pytest.mark.asyncio
async def test_signed_in_visitor_is_sent_to_the_dashboard(session):
    response = await landing(_Request(), user=object(), session=session)

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
