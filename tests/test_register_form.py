"""Form-level coverage for the repeated-password field on /register.

The match check is a *form* concern, not a password rule: create_user only ever sees one
password, so the service-level tests in test_email_auth cannot see this at all. That makes
a real request the only way to cover it — same shape as test_rate_limit_page (httpx over
ASGITransport, one shared in-memory DB), but without its Bearer shortcut: a form post has
to go through the CSRF middleware, which is half of what is being exercised here.

Config requires an API key at import time, so dummy env vars are set before importing app
modules. Needs httpx (a project dependency, present in the container); the local Python 3.9
env does not have it, so run these under Docker.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.csrf import CSRF_COOKIE_NAME, CSRF_FORM_FIELD
from app.db.session import get_session
from app.main import app
from app.models.base import Base
from app.models.signup_code import SignupCode
from app.models.user import User
from app.services.settings_service import set_signup_closed
from app.services.signup_code_service import create_code

USERNAME = "marvin"
EMAIL = "marvin@example.com"
PASSWORD = "hunter2-hunter2"


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared in-memory DB across every session opened
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_session():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = _override_session

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.maker = maker
        yield c

    app.dependency_overrides.clear()
    await engine.dispose()


async def _submit(client, **fields):
    """POST the register form the way a browser would, CSRF token and all.

    The double-submit pattern means the token has to come from a real GET first; the
    cookie jar carries the cookie half, and the value is echoed back as the form field.
    """
    page = await client.get("/register")
    assert page.status_code == 200
    token = client.cookies[CSRF_COOKIE_NAME]

    form = {
        "username": USERNAME,
        "email": EMAIL,
        "password": PASSWORD,
        "password_confirm": PASSWORD,
        CSRF_FORM_FIELD: token,
    }
    form.update(fields)
    return await client.post("/register", data=form)


async def _user_count(client) -> int:
    async with client.maker() as session:
        rows = await session.execute(select(User).where(User.username == USERNAME))
        return len(rows.scalars().all())


@pytest.mark.asyncio
async def test_mismatched_repeat_is_rejected(client):
    res = await _submit(client, password_confirm=PASSWORD + "-typo")

    assert res.status_code == 400
    assert "stimmen nicht überein" in res.text
    # The whole point of the field: a typo must not leave an account behind that the
    # user cannot log into.
    assert await _user_count(client) == 0


@pytest.mark.asyncio
async def test_a_missing_repeat_field_gets_the_form_back_not_a_422(client):
    """An empty (or absent) second field lands in the same German error, not raw JSON.

    This is why the parameter has a default instead of being required at the HTTP layer.
    """
    res = await _submit(client, password_confirm="")

    assert res.status_code == 400
    assert "stimmen nicht überein" in res.text
    assert await _user_count(client) == 0


@pytest.mark.asyncio
async def test_a_mismatch_does_not_burn_an_invite_seat(client):
    """A typo must cost the invite nothing — it is checked before the code is redeemed.

    Regression guard for the ordering: move the match check below signup_allowed() and an
    invite for 20 people quietly runs out early on retries.
    """
    async with client.maker() as session:
        await set_signup_closed(session, True)
        code = await create_code(session, max_uses=3)
        code_value = code.code

    res = await _submit(
        client, signup_code=code_value, password_confirm=PASSWORD + "-typo"
    )
    assert res.status_code == 400

    async with client.maker() as session:
        row = (
            await session.execute(
                select(SignupCode).where(SignupCode.code == code_value)
            )
        ).scalar_one()
        assert row.used_count == 0


@pytest.mark.asyncio
async def test_matching_passwords_still_register(client):
    res = await _submit(client)

    assert res.status_code == 303
    assert res.headers["location"] == "/dashboard"
    assert await _user_count(client) == 1
