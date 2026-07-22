"""Admin panel service layer: admin auth (mirrors ``auth_service`` but against the
separate ``adminuser``/``admintoken`` tables) plus the queries backing the panel's
pages."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import generate_token, hash_password, verify_password
from app.core.time import today_local
from app.models.admin_token import AdminToken
from app.models.admin_user import AdminUser
from app.models.ai_usage import AiUsage
from app.models.auth_token import AuthToken
from app.models.meal import Meal
from app.models.user import User
from app.services.ai_log_service import get_token_totals, token_totals_by_user
from app.services.usage_service import get_usage, limit_for


@dataclass
class UserRow:
    """One row of the admin user list."""

    username: str
    created_at: datetime
    tier: str
    meal_count: int
    last_meal_at: Optional[datetime]
    credits_used: int
    credit_limit: int
    tokens_total: int


@dataclass
class UserDetail:
    """Everything the admin detail page shows above the logs."""

    username: str
    email: Optional[str]
    email_verified_at: Optional[datetime]
    created_at: datetime
    tier: str
    credit_limit: int
    credits_today: int
    meal_count: int
    last_meal_at: Optional[datetime]
    active_sessions: int
    last_login_at: Optional[datetime]
    tokens_in: int
    tokens_out: int


@dataclass
class CreditDay:
    """One day's credit spend for a single user."""

    day: date
    count: int


async def authenticate_admin(
    session: AsyncSession, username: str, password: str
) -> Optional[AdminUser]:
    result = await session.execute(select(AdminUser).where(AdminUser.username == username))
    admin = result.scalar_one_or_none()
    if admin is None or not verify_password(password, admin.password_hash):
        return None
    admin.last_login_at = datetime.now(timezone.utc)
    await session.commit()
    return admin


async def create_admin_token(session: AsyncSession, admin: AdminUser) -> AdminToken:
    token = AdminToken(
        token=generate_token(),
        admin_id=admin.id,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.admin_session_ttl_days),
    )
    session.add(token)
    await session.commit()
    return token


async def get_admin_by_token(session: AsyncSession, token: str) -> Optional[AdminUser]:
    result = await session.execute(select(AdminToken).where(AdminToken.token == token))
    admin_token = result.scalar_one_or_none()
    if admin_token is None:
        return None
    if admin_token.expires_at is not None:
        expires_at = admin_token.expires_at
        if expires_at.tzinfo is None:  # SQLite may hand back naive datetimes
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return None
    result = await session.execute(select(AdminUser).where(AdminUser.id == admin_token.admin_id))
    return result.scalar_one_or_none()


async def delete_admin_token(session: AsyncSession, token: str) -> None:
    result = await session.execute(select(AdminToken).where(AdminToken.token == token))
    admin_token = result.scalar_one_or_none()
    if admin_token is not None:
        await session.delete(admin_token)
        await session.commit()


async def ensure_bootstrap_admin(session: AsyncSession) -> Optional[AdminUser]:
    """Create (or re-key) the admin account from ADMIN_USERNAME/ADMIN_PASSWORD.

    No-op when either env var is unset. When the admin already exists its password
    hash is refreshed, so changing the env var and restarting recovers access
    without shell access to the container.
    """
    username = settings.admin_username.strip()
    password = settings.admin_password
    if not username or not password:
        return None
    result = await session.execute(select(AdminUser).where(AdminUser.username == username))
    admin = result.scalar_one_or_none()
    if admin is None:
        admin = AdminUser(username=username, password_hash=hash_password(password))
        session.add(admin)
    else:
        admin.password_hash = hash_password(password)
    await session.commit()
    await session.refresh(admin)
    return admin


async def set_user_tier(session: AsyncSession, username: str, tier: str) -> bool:
    """Move a user to another tier. Returns False when the user does not exist.

    ``tier_daily_credits`` is the only source of truth for which tiers exist, so a
    value it does not know is rejected here rather than written and silently
    downgraded to "free" by ``limit_for`` on every later request.
    """
    if tier not in settings.tier_daily_credits:
        raise ValueError(f"unknown tier: {tier}")
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        return False
    user.tier = tier
    await session.commit()
    return True


async def list_users_with_stats(session: AsyncSession) -> list[UserRow]:
    """All app users, newest first, with their activity counters.

    Note the join condition: ``Meal``/``VoiceUsage`` reference a user by *username*
    (``user_id`` is a String), not by ``User.id`` — there is no FK between them.
    """
    stmt = (
        select(
            User.username,
            User.created_at,
            User.tier,
            func.count(Meal.id).label("meal_count"),
            func.max(Meal.timestamp).label("last_meal_at"),
        )
        .outerjoin(Meal, Meal.user_id == User.username)
        .group_by(User.id)
        .order_by(User.created_at.desc())
    )
    rows = (await session.execute(stmt)).all()

    # Second query rather than another join: joining two one-to-many tables at once
    # would multiply the meal count by the number of usage rows. The app-wide
    # ``GLOBAL_KEY`` row lives in the same table but is never looked up here, since
    # we only index by real usernames.
    usage_stmt = select(AiUsage.user_id, AiUsage.count).where(AiUsage.day == today_local())
    credits_by_user = {u: c for u, c in (await session.execute(usage_stmt)).all()}
    tokens_by_user = await token_totals_by_user(session)

    return [
        UserRow(
            username=row.username,
            created_at=row.created_at,
            tier=row.tier,
            meal_count=row.meal_count or 0,
            last_meal_at=row.last_meal_at,
            credits_used=credits_by_user.get(row.username, 0),
            credit_limit=limit_for(row.tier),
            tokens_total=sum(tokens_by_user.get(row.username, (0, 0))),
        )
        for row in rows
    ]


async def get_user_detail(session: AsyncSession, username: str) -> Optional[UserDetail]:
    """One user's profile and counters, or None when the name is unknown.

    Several small queries rather than one join: ``Meal`` and ``AuthToken`` are both
    one-to-many against the user, so joining them together would multiply each
    other's counts — the same trap ``list_users_with_stats`` sidesteps.
    """
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        return None

    meal_stats = (
        await session.execute(
            select(func.count(Meal.id), func.max(Meal.timestamp)).where(
                Meal.user_id == username
            )
        )
    ).one()

    # Compared in SQL rather than in Python: SQLite returns naive datetimes, and
    # an aware "now" would raise on comparison — see get_admin_by_token above,
    # which has to work around exactly that after the fact.
    now = datetime.now(timezone.utc)
    session_stats = (
        await session.execute(
            select(func.count(AuthToken.token), func.max(AuthToken.created_at)).where(
                AuthToken.user_id == user.id,
                or_(AuthToken.expires_at.is_(None), AuthToken.expires_at > now),
            )
        )
    ).one()

    tokens_in, tokens_out = await get_token_totals(session, username)

    return UserDetail(
        username=user.username,
        email=user.email,
        email_verified_at=user.email_verified_at,
        created_at=user.created_at,
        tier=user.tier,
        credit_limit=limit_for(user.tier),
        credits_today=await get_usage(session, username),
        meal_count=meal_stats[0] or 0,
        last_meal_at=meal_stats[1],
        active_sessions=session_stats[0] or 0,
        # Newest live session standing in for a real last-login timestamp, which
        # the user table does not carry.
        last_login_at=session_stats[1],
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )


async def list_user_credit_days(
    session: AsyncSession, username: str, days: int = 30
) -> list[CreditDay]:
    """Recent daily credit spend, newest first.

    Filtering on the username also excludes ``usage_service.GLOBAL_KEY``, which
    shares this table but is the app-wide counter, not a user.
    """
    cutoff = today_local() - timedelta(days=days)
    result = await session.execute(
        select(AiUsage.day, AiUsage.count)
        .where(AiUsage.user_id == username, AiUsage.day > cutoff)
        .order_by(AiUsage.day.desc())
    )
    return [CreditDay(day=day, count=count) for day, count in result.all()]


async def list_user_meals(
    session: AsyncSession, username: str, limit: int = 20
) -> list[Meal]:
    result = await session.execute(
        select(Meal)
        .where(Meal.user_id == username)
        .order_by(Meal.timestamp.desc(), Meal.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
