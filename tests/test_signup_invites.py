"""Tests for admin-generated invite codes and the registration gate they feed.

The env-var code path is covered by test_signup_code.py; this covers the DB-backed
codes, the panel toggle, and how the two combine. Config requires an API key at import
time, so dummy env vars are set before importing app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base
from app.models.app_setting import AppSetting  # noqa: F401 — register with Base.metadata
from app.models.signup_code import SignupCode
from app.services.settings_service import is_signup_closed, set_signup_closed
from app.services.signup_code_service import (
    _ALPHABET,
    create_code,
    generate_code,
    list_codes,
    redeem_code,
    refund_code,
    revoke_code,
    signup_allowed,
    signup_requires_code,
)


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s


@pytest.fixture(autouse=True)
def no_env_code(monkeypatch):
    """Default to the env code being unset, so tests exercise the DB path."""
    monkeypatch.setattr(settings, "signup_code", "")


# --- code generation ---------------------------------------------------------


def test_generated_codes_avoid_ambiguous_characters():
    for _ in range(50):
        code = generate_code()
        assert len(code) == 8
        assert set(code) <= set(_ALPHABET)
        assert not (set(code) & set("IO01"))


# --- redemption --------------------------------------------------------------


@pytest.mark.asyncio
async def test_code_can_be_redeemed_up_to_its_limit(session):
    code = await create_code(session, max_uses=2)
    assert await redeem_code(session, code.code) is True
    assert await redeem_code(session, code.code) is True
    assert await redeem_code(session, code.code) is False  # third one is over the limit


@pytest.mark.asyncio
async def test_redemption_is_case_insensitive_and_trims(session):
    code = await create_code(session, max_uses=1)
    assert await redeem_code(session, "  " + code.code.lower() + " ") is True


@pytest.mark.asyncio
async def test_unknown_and_empty_codes_are_rejected(session):
    assert await redeem_code(session, "NOPE1234") is False
    assert await redeem_code(session, "") is False
    assert await redeem_code(session, "   ") is False


@pytest.mark.asyncio
async def test_revoked_code_is_rejected(session):
    code = await create_code(session, max_uses=5)
    assert await revoke_code(session, code.id) is True
    assert await redeem_code(session, code.code) is False
    assert await revoke_code(session, code.id) is False  # already revoked


@pytest.mark.asyncio
async def test_expired_code_is_rejected(session):
    code = await create_code(session, max_uses=5)
    code.expires_at = datetime.utcnow() - timedelta(hours=1)
    await session.commit()
    assert await redeem_code(session, code.code) is False


@pytest.mark.asyncio
async def test_unexpired_code_is_accepted(session):
    code = await create_code(session, max_uses=5, valid_days=7)
    assert code.expires_at is not None
    assert await redeem_code(session, code.code) is True


@pytest.mark.asyncio
async def test_concurrent_redemptions_cannot_oversell_the_last_seat(engine):
    """Two registrations racing for one remaining seat: exactly one may win."""
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        code = await create_code(s, max_uses=1)
    plain = code.code

    async def attempt() -> bool:
        async with maker() as s:
            return await redeem_code(s, plain)

    results = await asyncio.gather(attempt(), attempt(), return_exceptions=True)
    successes = [r for r in results if r is True]
    assert len(successes) == 1

    async with maker() as s:
        row = (
            await s.execute(select(SignupCode).where(SignupCode.code == plain))
        ).scalar_one()
        assert row.used_count == 1  # never above max_uses


# --- refund ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refund_returns_a_seat(session):
    code = await create_code(session, max_uses=1)
    assert await redeem_code(session, code.code) is True
    await refund_code(session, code.code)
    assert await redeem_code(session, code.code) is True  # seat is available again


@pytest.mark.asyncio
async def test_refund_never_pushes_the_counter_negative(session):
    code = await create_code(session, max_uses=1)
    await refund_code(session, code.code)
    await refund_code(session, code.code)
    rows = await list_codes(session)
    assert rows[0].used_count == 0


@pytest.mark.asyncio
async def test_refund_ignores_unknown_and_empty_codes(session):
    await refund_code(session, "NOPE1234")
    await refund_code(session, "")


# --- listing -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_reports_status_and_remaining(session):
    active = await create_code(session, max_uses=3, label="Instagram")
    used_up = await create_code(session, max_uses=1)
    await redeem_code(session, used_up.code)
    revoked = await create_code(session, max_uses=5)
    await revoke_code(session, revoked.id)
    expired = await create_code(session, max_uses=5)
    expired.expires_at = datetime.utcnow() - timedelta(days=1)
    await session.commit()

    by_code = {r.code: r for r in await list_codes(session)}
    assert by_code[active.code].status == "active"
    assert by_code[active.code].remaining == 3
    assert by_code[active.code].label == "Instagram"
    assert by_code[used_up.code].status == "used_up"
    assert by_code[used_up.code].remaining == 0
    assert by_code[revoked.code].status == "revoked"
    assert by_code[expired.code].status == "expired"


@pytest.mark.asyncio
async def test_create_rejects_nonsense_limits(session):
    for bad in (0, -5):
        with pytest.raises(ValueError):
            await create_code(session, max_uses=bad)


@pytest.mark.asyncio
async def test_blank_label_is_stored_as_none(session):
    code = await create_code(session, max_uses=1, label="   ")
    assert code.label is None


# --- the registration gate ---------------------------------------------------


@pytest.mark.asyncio
async def test_signup_open_by_default(session):
    assert await is_signup_closed(session) is False
    assert await signup_requires_code(session) is False
    assert await signup_allowed(session, "") is True  # no code needed


@pytest.mark.asyncio
async def test_panel_toggle_closes_and_reopens_signup(session):
    await set_signup_closed(session, True)
    assert await signup_requires_code(session) is True
    assert await signup_allowed(session, "") is False

    await set_signup_closed(session, False)
    assert await signup_requires_code(session) is False
    assert await signup_allowed(session, "") is True


@pytest.mark.asyncio
async def test_closed_signup_accepts_a_generated_code(session):
    await set_signup_closed(session, True)
    code = await create_code(session, max_uses=1)
    assert await signup_allowed(session, code.code) is True
    assert await signup_allowed(session, code.code) is False  # seat is spent


@pytest.mark.asyncio
async def test_env_code_closes_signup_even_when_toggle_is_open(session, monkeypatch):
    monkeypatch.setattr(settings, "signup_code", "kraftsport2026")
    assert await is_signup_closed(session) is False
    assert await signup_requires_code(session) is True
    assert await signup_allowed(session, "") is False


@pytest.mark.asyncio
async def test_env_code_is_unlimited_and_consumes_no_seats(session, monkeypatch):
    monkeypatch.setattr(settings, "signup_code", "kraftsport2026")
    db_code = await create_code(session, max_uses=1)
    for _ in range(5):
        assert await signup_allowed(session, "kraftsport2026") is True
    # the DB code was never touched by those signups
    assert (await list_codes(session))[0].used_count == 0
    assert await signup_allowed(session, db_code.code) is True


@pytest.mark.asyncio
async def test_generated_code_still_works_alongside_the_env_code(session, monkeypatch):
    monkeypatch.setattr(settings, "signup_code", "kraftsport2026")
    code = await create_code(session, max_uses=1)
    assert await signup_allowed(session, code.code) is True
    assert await signup_allowed(session, "falsch") is False
