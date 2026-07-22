"""Tests for the admin service: bootstrap, admin auth/tokens, and the user list
with activity stats.

Like the other test modules these exercise the service layer directly against an
in-memory SQLite database (no HTTP/auth stack). Config requires an API key at
import time, so dummy env vars are set before importing app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models.base import Base
from app.models.admin_token import AdminToken  # noqa: F401 — register with Base.metadata
from app.models.admin_user import AdminUser
from app.models.ai_usage import AiUsage
from app.models.auth_token import AuthToken
from app.models.meal import Meal
from app.models.user import User
from app.models.user_token_total import UserTokenTotal
from app.services.admin_service import (
    authenticate_admin,
    create_admin_token,
    delete_admin_token,
    ensure_bootstrap_admin,
    get_admin_by_token,
    get_user_detail,
    list_user_credit_days,
    list_user_meals,
    list_users_with_stats,
    set_user_tier,
)
from app.services.usage_service import GLOBAL_KEY


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def admin_env(monkeypatch):
    """Set the bootstrap env vars on the already-instantiated settings object."""

    def _set(username: str, password: str):
        monkeypatch.setattr(settings, "admin_username", username)
        monkeypatch.setattr(settings, "admin_password", password)

    return _set


# --- bootstrap ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_creates_admin(session, admin_env):
    admin_env("root", "secret")
    admin = await ensure_bootstrap_admin(session)
    assert admin is not None
    assert admin.username == "root"
    assert await authenticate_admin(session, "root", "secret") is not None


@pytest.mark.asyncio
async def test_bootstrap_is_noop_without_env(session, admin_env):
    admin_env("", "")
    assert await ensure_bootstrap_admin(session) is None
    admin_env("root", "")  # password alone missing is also a no-op
    assert await ensure_bootstrap_admin(session) is None


@pytest.mark.asyncio
async def test_bootstrap_does_not_duplicate_and_resets_password(session, admin_env):
    admin_env("root", "secret")
    first = await ensure_bootstrap_admin(session)
    admin_env("root", "new-secret")
    second = await ensure_bootstrap_admin(session)
    assert second.id == first.id  # same row, not a second admin
    assert await authenticate_admin(session, "root", "new-secret") is not None
    assert await authenticate_admin(session, "root", "secret") is None


# --- authentication ----------------------------------------------------------


@pytest.mark.asyncio
async def test_authenticate_rejects_wrong_password_and_unknown_user(session):
    session.add(AdminUser(username="root", password_hash=hash_password("secret")))
    await session.commit()
    assert await authenticate_admin(session, "root", "wrong") is None
    assert await authenticate_admin(session, "nobody", "secret") is None


@pytest.mark.asyncio
async def test_authenticate_records_last_login(session):
    session.add(AdminUser(username="root", password_hash=hash_password("secret")))
    await session.commit()
    admin = await authenticate_admin(session, "root", "secret")
    assert admin.last_login_at is not None


# --- tokens ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_roundtrip(session):
    admin = AdminUser(username="root", password_hash=hash_password("secret"))
    session.add(admin)
    await session.commit()
    token = await create_admin_token(session, admin)
    resolved = await get_admin_by_token(session, token.token)
    assert resolved.username == "root"

    await delete_admin_token(session, token.token)
    assert await get_admin_by_token(session, token.token) is None


@pytest.mark.asyncio
async def test_unknown_and_expired_tokens_resolve_to_none(session):
    admin = AdminUser(username="root", password_hash=hash_password("secret"))
    session.add(admin)
    await session.commit()
    session.add(
        AdminToken(
            token="expired",
            admin_id=admin.id,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
    )
    await session.commit()
    assert await get_admin_by_token(session, "does-not-exist") is None
    assert await get_admin_by_token(session, "expired") is None


# --- user list ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_list_without_activity(session):
    session.add(User(username="alice", password_hash="x"))
    await session.commit()
    rows = await list_users_with_stats(session)
    assert len(rows) == 1
    assert rows[0].username == "alice"
    assert rows[0].meal_count == 0  # outer join must not drop the user
    assert rows[0].last_meal_at is None
    assert rows[0].credits_used == 0
    assert rows[0].tier == "free"
    assert rows[0].credit_limit == settings.tier_daily_credits["free"]


@pytest.mark.asyncio
async def test_user_list_counts_meals_and_last_activity(session):
    session.add_all(
        [
            User(username="alice", password_hash="x"),
            User(username="bob", password_hash="x"),
        ]
    )
    await session.commit()
    older = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    newer = datetime(2026, 7, 5, 18, 30, tzinfo=timezone.utc)
    session.add_all(
        [
            Meal(user_id="alice", description="Haferflocken", timestamp=older),
            Meal(user_id="alice", description="Reis", timestamp=newer),
            Meal(user_id="bob", description="Skyr", timestamp=older),
        ]
    )
    await session.commit()

    by_name = {r.username: r for r in await list_users_with_stats(session)}
    assert by_name["alice"].meal_count == 2
    assert by_name["alice"].last_meal_at.replace(tzinfo=timezone.utc) == newer
    assert by_name["bob"].meal_count == 1


@pytest.mark.asyncio
async def test_credit_count_only_counts_today(session, monkeypatch):
    today = datetime(2026, 7, 18).date()
    monkeypatch.setattr("app.services.admin_service.today_local", lambda: today)
    session.add(User(username="alice", password_hash="x"))
    await session.commit()
    session.add_all(
        [
            AiUsage(user_id="alice", day=today, count=4),
            AiUsage(user_id="alice", day=today - timedelta(days=1), count=9),
        ]
    )
    await session.commit()

    rows = await list_users_with_stats(session)
    assert rows[0].credits_used == 4


@pytest.mark.asyncio
async def test_credit_limit_follows_tier_and_global_row_is_ignored(session, monkeypatch):
    """The app-wide GLOBAL_KEY counter shares the ai_usage table but is not a user."""
    today = datetime(2026, 7, 18).date()
    monkeypatch.setattr("app.services.admin_service.today_local", lambda: today)
    session.add_all(
        [
            User(username="alice", password_hash="x", tier="pro"),
            User(username="bob", password_hash="x", tier="free"),
        ]
    )
    await session.commit()
    session.add(AiUsage(user_id=GLOBAL_KEY, day=today, count=300))
    await session.commit()

    rows = await list_users_with_stats(session)
    by_name = {r.username: r for r in rows}
    assert len(rows) == 2  # the global row must not show up as a user
    assert by_name["alice"].credit_limit == settings.tier_daily_credits["pro"]
    assert by_name["bob"].credit_limit == settings.tier_daily_credits["free"]
    assert by_name["alice"].credits_used == 0


@pytest.mark.asyncio
async def test_user_list_orders_newest_first(session):
    session.add_all(
        [
            User(
                username="old",
                password_hash="x",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
            User(
                username="new",
                password_hash="x",
                created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            ),
        ]
    )
    await session.commit()
    rows = await list_users_with_stats(session)
    assert [r.username for r in rows] == ["new", "old"]


# --- tier changes ------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_user_tier_raises_the_daily_limit(session):
    session.add(User(username="alice", password_hash="x", tier="free"))
    await session.commit()

    assert await set_user_tier(session, "alice", "pro") is True

    rows = await list_users_with_stats(session)
    assert rows[0].tier == "pro"
    assert rows[0].credit_limit == settings.tier_daily_credits["pro"]


@pytest.mark.asyncio
async def test_set_user_tier_rejects_unknown_tier(session):
    """An unknown tier would be silently downgraded to "free" by limit_for later."""
    session.add(User(username="alice", password_hash="x", tier="free"))
    await session.commit()

    with pytest.raises(ValueError):
        await set_user_tier(session, "alice", "platinum")

    rows = await list_users_with_stats(session)
    assert rows[0].tier == "free"


@pytest.mark.asyncio
async def test_set_user_tier_reports_missing_user(session):
    assert await set_user_tier(session, "nobody", "pro") is False


# --- user detail -------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_detail_reports_missing_user(session):
    assert await get_user_detail(session, "nobody") is None


@pytest.mark.asyncio
async def test_user_detail_reports_profile_and_activity(session, monkeypatch):
    today = datetime(2026, 7, 18).date()
    monkeypatch.setattr("app.services.usage_service.today_local", lambda: today)
    verified = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    session.add(
        User(
            username="alice",
            email="alice@example.com",
            email_verified_at=verified,
            password_hash="x",
            tier="pro",
        )
    )
    await session.commit()
    older = datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)
    newer = datetime(2026, 7, 6, 18, 30, tzinfo=timezone.utc)
    session.add_all(
        [
            Meal(user_id="alice", description="Haferflocken", timestamp=older),
            Meal(user_id="alice", description="Reis", timestamp=newer),
            Meal(user_id="bob", description="Skyr", timestamp=newer),
        ]
    )
    session.add(AiUsage(user_id="alice", day=today, count=7))
    session.add(
        UserTokenTotal(user_id="alice", prompt_tokens=1200, completion_tokens=340)
    )
    await session.commit()

    detail = await get_user_detail(session, "alice")
    assert detail.email == "alice@example.com"
    assert detail.email_verified_at.replace(tzinfo=timezone.utc) == verified
    assert detail.tier == "pro"
    assert detail.credit_limit == settings.tier_daily_credits["pro"]
    assert detail.credits_today == 7
    assert detail.meal_count == 2  # bob's meal must not be counted
    assert detail.last_meal_at.replace(tzinfo=timezone.utc) == newer
    assert (detail.tokens_in, detail.tokens_out) == (1200, 340)


@pytest.mark.asyncio
async def test_user_detail_reports_zero_tokens_when_never_counted(session):
    session.add(User(username="alice", password_hash="x"))
    await session.commit()

    detail = await get_user_detail(session, "alice")
    assert (detail.tokens_in, detail.tokens_out) == (0, 0)


@pytest.mark.asyncio
async def test_user_list_sums_tokens_per_user(session):
    session.add_all(
        [
            User(username="alice", password_hash="x"),
            User(username="bob", password_hash="x"),
        ]
    )
    session.add(
        UserTokenTotal(user_id="alice", prompt_tokens=1000, completion_tokens=250)
    )
    await session.commit()

    by_name = {r.username: r for r in await list_users_with_stats(session)}
    assert by_name["alice"].tokens_total == 1250
    assert by_name["bob"].tokens_total == 0  # no counter row yet


@pytest.mark.asyncio
async def test_user_detail_counts_only_live_sessions(session):
    user = User(username="alice", password_hash="x")
    session.add(user)
    await session.commit()
    now = datetime.now(timezone.utc)
    session.add_all(
        [
            AuthToken(token="no-expiry", user_id=user.id, expires_at=None),
            AuthToken(
                token="future", user_id=user.id, expires_at=now + timedelta(days=1)
            ),
            AuthToken(
                token="expired", user_id=user.id, expires_at=now - timedelta(days=1)
            ),
        ]
    )
    await session.commit()

    detail = await get_user_detail(session, "alice")
    assert detail.active_sessions == 2


@pytest.mark.asyncio
async def test_credit_days_ignore_global_row_and_order_newest_first(session):
    today = datetime(2026, 7, 18).date()
    session.add(User(username="alice", password_hash="x"))
    await session.commit()
    session.add_all(
        [
            AiUsage(user_id="alice", day=today - timedelta(days=2), count=3),
            AiUsage(user_id="alice", day=today, count=5),
            AiUsage(user_id=GLOBAL_KEY, day=today, count=400),
        ]
    )
    await session.commit()

    days = await list_user_credit_days(session, "alice")
    assert [(d.day, d.count) for d in days] == [(today, 5), (today - timedelta(days=2), 3)]


@pytest.mark.asyncio
async def test_user_meals_are_scoped_ordered_and_capped(session):
    session.add(User(username="alice", password_hash="x"))
    await session.commit()
    base = datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc)
    session.add_all(
        [
            Meal(user_id="alice", description="erste", timestamp=base),
            Meal(user_id="alice", description="zweite", timestamp=base + timedelta(hours=3)),
            Meal(user_id="bob", description="fremd", timestamp=base + timedelta(hours=4)),
        ]
    )
    await session.commit()

    meals = await list_user_meals(session, "alice")
    assert [m.description for m in meals] == ["zweite", "erste"]
    assert len(await list_user_meals(session, "alice", limit=1)) == 1
