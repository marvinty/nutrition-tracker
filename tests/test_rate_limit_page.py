"""End-to-end coverage for the 429 credit-limit response on the AI endpoints.

Unlike test_usage (which exercises consume_credits at the service layer), these drive a
real request through the whole stack — dependencies, the credit charge, the rollback it
does on a refusal, and the exception handler that turns the 429 into a response. That
combination is exactly what a service-level test cannot see, and it is where the bug
lived: consume_credits rolls the request session back before re-raising 429, which
expires every ORM object on it, and the error page then rendered the e-mail-verification
banner off the now-expired User — a DetachedInstanceError that surfaced as a 500 instead
of the intended limit page.

Config requires an API key at import time, so dummy env vars are set before importing
app modules. Needs httpx (a project dependency, present in the container); the local
Python 3.9 env does not have it, so run these under Docker.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import get_session
from app.main import app
from app.models.base import Base
from app.providers import get_provider
from app.services.auth_service import create_token, create_user

# The account for these tests is deliberately left unverified but still inside its grace
# period: unverified is what makes resolve_user populate the verification banner (the
# thing that used to crash the error page), and inside-grace is what keeps it from being
# redirected to /verify-email/required before it ever reaches the credit charge.
EMAIL = "marvin@example.com"
PASSWORD = "hunter2-hunter2"


@pytest_asyncio.fixture
async def client(monkeypatch):
    # A free budget of zero means the very first text log is refused, so no prior usage
    # has to be seeded to reach the 429 path. The global ceiling stays high so it is the
    # per-user limit that trips, matching the reported case.
    monkeypatch.setattr(settings, "tier_daily_credits", {"free": 0, "pro": 300})
    monkeypatch.setattr(settings, "global_daily_credits", 500)
    monkeypatch.setattr(settings, "email_verify_grace_minutes", 60)

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared in-memory DB across every session opened
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with maker() as setup:
        user = await create_user(setup, "marvin", EMAIL, PASSWORD)
        token = await create_token(setup, user)
        token_value = token.token

    async def _override_session():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = _override_session
    # The credit check raises before the endpoint touches a provider, so a stub keeps the
    # test from constructing a real LLM client.
    app.dependency_overrides[get_provider] = lambda: None

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # Bearer auth is exempt from the CSRF middleware, which keeps the test to the code
        # path under test; the 429 handler keys on Accept, not on how the caller authed.
        c.headers["Authorization"] = f"Bearer {token_value}"
        yield c

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_browser_navigation_gets_the_limit_page_not_a_500(client):
    """A form-style navigation (Accept: text/html) renders the page, banner and all.

    Regression guard: the rollback consume_credits does on a 429 expires the User the
    banner used to read at render time, which turned this into a 500.
    """
    res = await client.post(
        "/meals/text",
        json={"text": "100g chicken breast"},
        headers={"Accept": "text/html"},
    )

    assert res.status_code == 429
    assert "Tägliches Limit" in res.text
    # The banner is the exact thing that crashed: prove it actually rendered, off the
    # rolled-back session, so a future change that drops it does not quietly gut this test.
    assert EMAIL in res.text


@pytest.mark.asyncio
async def test_dashboard_fetch_gets_json_it_can_parse(client):
    """The dashboard's fetch (Accept: */*) must get JSON, not the HTML page.

    /meals/text sits at the root for the ESP32 client but is called from fetch code that
    reads ``detail`` out of JSON, so a path-only heuristic handed it an unparseable page.
    """
    res = await client.post(
        "/meals/text",
        json={"text": "100g chicken breast"},
        headers={"Accept": "*/*"},
    )

    assert res.status_code == 429
    assert "Tägliches Limit" in res.json()["detail"]
