"""Admin panel service layer: admin auth (mirrors ``auth_service`` but against the
separate ``adminuser``/``admintoken`` tables) plus the read-only queries backing
the panel's pages."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import generate_token, hash_password, verify_password
from app.core.time import today_local
from app.models.admin_token import AdminToken
from app.models.admin_user import AdminUser
from app.models.ai_usage import AiUsage
from app.models.meal import Meal
from app.models.user import User
from app.services.usage_service import limit_for


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

    return [
        UserRow(
            username=row.username,
            created_at=row.created_at,
            tier=row.tier,
            meal_count=row.meal_count or 0,
            last_meal_at=row.last_meal_at,
            credits_used=credits_by_user.get(row.username, 0),
            credit_limit=limit_for(row.tier),
        )
        for row in rows
    ]
