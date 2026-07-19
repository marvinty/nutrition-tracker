"""Tests for email-based identity: registration, verification and password reset.

Covers the service layer directly, matching the rest of the suite — there is no
TestClient in this project, so cookies, redirects and form parsing are verified by
hand against a running container instead.

Config requires an API key at import time, so dummy env vars are set before importing
app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import (
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN_LENGTH,
    InvalidEmailError,
    InvalidPasswordError,
    normalize_email,
    validate_password,
    verify_password,
)
from app.models.auth_token import AuthToken
from app.models.base import Base
from app.models.user import User
from app.services.auth_service import (
    RESET_TOKEN,
    SESSION_TOKEN,
    VERIFY_TOKEN,
    EmailTakenError,
    UsernameTakenError,
    authenticate_user,
    create_token,
    create_user,
    get_user_by_email,
    get_user_by_token,
    is_locked_for_unverified_email,
    latest_token_created_at,
    mark_email_verified,
    reset_password,
)


# Fixture password. Named rather than inlined because it now has to clear
# PASSWORD_MIN_LENGTH — a bare literal invites a too-short value creeping back in.
PASSWORD = "hunter2-hunter2"


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
def one_hour_grace(monkeypatch):
    monkeypatch.setattr(settings, "email_verify_grace_minutes", 60)


async def _make_user(session, username="marvin", email="marvin@example.com"):
    return await create_user(session, username, email, PASSWORD)


# --- address normalization ---------------------------------------------------


def test_normalize_email_lowercases_and_strips():
    assert normalize_email("  Marvin@Example.DE ") == "marvin@example.de"


@pytest.mark.parametrize(
    "bad", ["", "marvin", "marvin@", "@example.de", "marvin@example", "a b@example.de"]
)
def test_normalize_email_rejects_malformed(bad):
    with pytest.raises(InvalidEmailError):
        normalize_email(bad)


@pytest.mark.asyncio
async def test_case_variants_collide_as_the_same_account(session):
    """Normalizing on write is what makes the unique constraint meaningful."""
    await _make_user(session, email=normalize_email("Marvin@Example.de"))
    with pytest.raises(EmailTakenError):
        await create_user(
            session, "other", normalize_email("MARVIN@example.DE"), PASSWORD
        )


# --- registration ------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_email_is_rejected(session):
    await _make_user(session)
    with pytest.raises(EmailTakenError):
        await create_user(session, "someone-else", "marvin@example.com", PASSWORD)


@pytest.mark.asyncio
async def test_duplicate_username_still_rejected(session):
    await _make_user(session)
    with pytest.raises(UsernameTakenError):
        await create_user(session, "marvin", "other@example.com", PASSWORD)


@pytest.mark.asyncio
async def test_new_account_starts_unverified(session):
    user = await _make_user(session)
    assert user.email_verified_at is None


# --- password rules ----------------------------------------------------------


@pytest.mark.parametrize("length", [0, 1, PASSWORD_MIN_LENGTH - 1])
def test_short_passwords_are_rejected(length):
    with pytest.raises(InvalidPasswordError) as exc:
        validate_password("a" * length)
    assert exc.value.reason == "too_short"


def test_the_minimum_itself_is_accepted():
    """Guards the boundary against an off-by-one turning 10 into 11."""
    assert validate_password("a" * PASSWORD_MIN_LENGTH)


def test_a_long_passphrase_without_digits_is_accepted():
    """Deliberate: composition rules are not enforced, only length.

    A passphrase like this is stronger than "Passwort1", which a digit requirement
    would wave through — see the comment on PASSWORD_MIN_LENGTH.
    """
    assert validate_password("correct horse battery staple")


def test_passwords_past_the_bcrypt_limit_are_rejected():
    with pytest.raises(InvalidPasswordError) as exc:
        validate_password("a" * (PASSWORD_MAX_BYTES + 1))
    assert exc.value.reason == "too_long"


def test_the_limit_counts_bytes_not_characters():
    """Umlauts cost two bytes, and bcrypt truncates on bytes.

    Counting characters here would let a password through whose tail bcrypt silently
    ignores — the exact failure the limit exists to prevent.
    """
    password = "ü" * 40  # 40 characters, 80 bytes
    assert len(password) < PASSWORD_MAX_BYTES
    with pytest.raises(InvalidPasswordError) as exc:
        validate_password(password)
    assert exc.value.reason == "too_long"


def test_surrounding_whitespace_is_not_trimmed_away():
    """Trimming here but not on login would lock people out of their own accounts."""
    assert validate_password("  " + "a" * PASSWORD_MIN_LENGTH + "  ")


@pytest.mark.asyncio
async def test_registration_enforces_the_minimum(session):
    with pytest.raises(InvalidPasswordError):
        await create_user(session, "marvin", "marvin@example.com", "kurz")


@pytest.mark.asyncio
async def test_a_rejected_password_creates_no_account(session):
    """The check has to land before the insert, not alongside it."""
    with pytest.raises(InvalidPasswordError):
        await create_user(session, "marvin", "marvin@example.com", "kurz")
    assert await get_user_by_email(session, "marvin@example.com") is None


@pytest.mark.asyncio
async def test_reset_enforces_the_minimum(session):
    """Reset is the other way to set a password, and the way around the rule if missed."""
    user = await _make_user(session)
    with pytest.raises(InvalidPasswordError):
        await reset_password(session, user, "kurz")
    assert verify_password(PASSWORD, user.password_hash)


# --- login -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_by_email(session):
    await _make_user(session)
    assert await authenticate_user(session, "marvin@example.com", PASSWORD) is not None


@pytest.mark.asyncio
async def test_login_accepts_unnormalized_email(session):
    await _make_user(session)
    assert await authenticate_user(session, " MARVIN@example.COM ", PASSWORD) is not None


@pytest.mark.asyncio
async def test_login_by_username_no_longer_works(session):
    """The username is a display name now; only the address authenticates."""
    await _make_user(session)
    assert await authenticate_user(session, "marvin", PASSWORD) is None


@pytest.mark.asyncio
async def test_login_with_wrong_password(session):
    await _make_user(session)
    assert await authenticate_user(session, "marvin@example.com", "wrong") is None


# --- verification lock -------------------------------------------------------


@pytest.mark.asyncio
async def test_not_locked_inside_grace_period(session):
    user = await _make_user(session)
    assert is_locked_for_unverified_email(user) is False


@pytest.mark.asyncio
async def test_locked_once_grace_period_lapses(session):
    user = await _make_user(session)
    user.created_at = datetime.now(timezone.utc) - timedelta(minutes=61)
    assert is_locked_for_unverified_email(user) is True


@pytest.mark.asyncio
async def test_verifying_unlocks_a_locked_account(session):
    user = await _make_user(session)
    user.created_at = datetime.now(timezone.utc) - timedelta(days=3)
    assert is_locked_for_unverified_email(user) is True
    await mark_email_verified(session, user)
    assert is_locked_for_unverified_email(user) is False


@pytest.mark.asyncio
async def test_naive_created_at_is_read_as_utc(session):
    """SQLite returns naive datetimes; comparing them as local time would misfire."""
    user = await _make_user(session)
    user.created_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(
        tzinfo=None
    )
    assert is_locked_for_unverified_email(user) is False


@pytest.mark.asyncio
async def test_grandfathered_user_is_never_locked(session):
    """What the migration backfill produces: old account, no address, marked verified.

    Without the backfill every pre-existing user would be past the deadline the moment
    this ships and would be locked out of an app they were just using.
    """
    user = User(
        username="oldtimer",
        email=None,
        password_hash="x",
        created_at=datetime.now(timezone.utc) - timedelta(days=400),
        email_verified_at=datetime.now(timezone.utc) - timedelta(days=400),
    )
    session.add(user)
    await session.commit()
    assert is_locked_for_unverified_email(user) is False


@pytest.mark.asyncio
async def test_migration_backfills_existing_users(engine):
    """Drive the real migration against a table shaped like the pre-email schema."""
    from app.db.init_db import _add_user_email_columns

    async with engine.begin() as conn:
        await conn.execute(text('DROP TABLE "user"'))
        await conn.execute(
            text(
                'CREATE TABLE "user" (id INTEGER PRIMARY KEY, username TEXT NOT NULL, '
                "password_hash TEXT NOT NULL, created_at DATETIME NOT NULL, "
                "tier TEXT NOT NULL DEFAULT 'free')"
            )
        )
        await conn.execute(
            text(
                'INSERT INTO "user" (username, password_hash, created_at) '
                "VALUES ('oldtimer', 'x', '2024-01-01 00:00:00')"
            )
        )
        await _add_user_email_columns(conn)
        result = await conn.execute(
            text('SELECT email, email_verified_at FROM "user" WHERE username = \'oldtimer\'')
        )
        email, verified_at = result.one()

    assert email is None
    assert verified_at is not None  # grandfathered, so never locked out


@pytest.mark.asyncio
async def test_migration_is_idempotent(engine):
    """It runs on every boot, so a second pass must be a no-op rather than an error."""
    from app.db.init_db import _add_user_email_columns

    async with engine.begin() as conn:
        await _add_user_email_columns(conn)
        await _add_user_email_columns(conn)


# --- tokens ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_token_is_not_accepted_as_a_session(session):
    """The reason verify/reset tokens can share the session table at all.

    A confirmation link travels through inboxes, forwards and proxy logs. If it also
    authenticated as a session cookie, anyone who saw the URL would hold a 30-day login.
    """
    user = await _make_user(session)
    token = await create_token(session, user, kind=VERIFY_TOKEN)
    assert await get_user_by_token(session, token.token, kind=SESSION_TOKEN) is None
    assert await get_user_by_token(session, token.token, kind=VERIFY_TOKEN) is not None


@pytest.mark.asyncio
async def test_reset_token_is_not_accepted_as_a_session(session):
    user = await _make_user(session)
    token = await create_token(session, user, kind=RESET_TOKEN)
    assert await get_user_by_token(session, token.token, kind=SESSION_TOKEN) is None


@pytest.mark.asyncio
async def test_session_token_is_not_accepted_as_a_verify_token(session):
    """The guard has to hold both ways, or a session cookie could confirm an address."""
    user = await _make_user(session)
    token = await create_token(session, user)
    assert await get_user_by_token(session, token.token, kind=VERIFY_TOKEN) is None


@pytest.mark.asyncio
async def test_expired_token_is_rejected(session):
    user = await _make_user(session)
    token = await create_token(session, user, kind=VERIFY_TOKEN)
    token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await session.commit()
    assert await get_user_by_token(session, token.token, kind=VERIFY_TOKEN) is None


@pytest.mark.asyncio
async def test_verifying_consumes_the_token(session):
    user = await _make_user(session)
    token = await create_token(session, user, kind=VERIFY_TOKEN)
    await mark_email_verified(session, user)
    assert user.email_verified_at is not None
    assert await get_user_by_token(session, token.token, kind=VERIFY_TOKEN) is None


@pytest.mark.asyncio
async def test_latest_token_created_at_drives_resend_throttle(session):
    user = await _make_user(session)
    assert await latest_token_created_at(session, user, VERIFY_TOKEN) is None
    await create_token(session, user, kind=VERIFY_TOKEN)
    assert await latest_token_created_at(session, user, VERIFY_TOKEN) is not None


# --- password reset ----------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_sets_new_password(session):
    user = await _make_user(session)
    await reset_password(session, user, "new-secret")
    assert verify_password("new-secret", user.password_hash)
    assert await authenticate_user(session, "marvin@example.com", PASSWORD) is None


@pytest.mark.asyncio
async def test_reset_revokes_every_session(session):
    """A reset is how someone evicts an intruder — leaving sessions alive defeats it."""
    user = await _make_user(session)
    session_token = await create_token(session, user)
    reset_token = await create_token(session, user, kind=RESET_TOKEN)

    await reset_password(session, user, "new-secret")

    assert await get_user_by_token(session, session_token.token) is None
    assert await get_user_by_token(session, reset_token.token, kind=RESET_TOKEN) is None
    remaining = await session.execute(
        select(AuthToken).where(AuthToken.user_id == user.id)
    )
    assert remaining.scalars().all() == []


@pytest.mark.asyncio
async def test_reset_also_verifies_the_address(session):
    """Reaching the link proves control of the mailbox, which is what verification is."""
    user = await _make_user(session)
    assert user.email_verified_at is None
    await reset_password(session, user, "new-secret")
    assert user.email_verified_at is not None


@pytest.mark.asyncio
async def test_reset_keeps_the_original_verification_time(session):
    user = await _make_user(session)
    await mark_email_verified(session, user)
    verified_at = user.email_verified_at
    await reset_password(session, user, "new-secret")
    assert user.email_verified_at == verified_at


@pytest.mark.asyncio
async def test_unknown_address_lookup_returns_none(session):
    """What keeps /forgot-password from confirming which addresses have accounts."""
    assert await get_user_by_email(session, "nobody@example.com") is None
