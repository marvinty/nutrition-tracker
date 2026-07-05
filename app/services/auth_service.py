from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import generate_token, hash_password, verify_password
from app.models.auth_token import AuthToken
from app.models.user import User


class UsernameTakenError(Exception):
    """Raised when trying to create a user whose username already exists."""


async def create_user(session: AsyncSession, username: str, password: str) -> User:
    existing = await session.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none() is not None:
        raise UsernameTakenError(username)
    user = User(username=username, password_hash=hash_password(password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(
    session: AsyncSession, username: str, password: str
) -> Optional[User]:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


async def create_token(session: AsyncSession, user: User, kind: str = "session") -> AuthToken:
    token = AuthToken(
        token=generate_token(),
        user_id=user.id,
        kind=kind,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days),
    )
    session.add(token)
    await session.commit()
    return token


async def get_user_by_token(session: AsyncSession, token: str) -> Optional[User]:
    result = await session.execute(select(AuthToken).where(AuthToken.token == token))
    auth_token = result.scalar_one_or_none()
    if auth_token is None:
        return None
    if auth_token.expires_at is not None:
        expires_at = auth_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return None
    result = await session.execute(select(User).where(User.id == auth_token.user_id))
    return result.scalar_one_or_none()


async def delete_token(session: AsyncSession, token: str) -> None:
    result = await session.execute(select(AuthToken).where(AuthToken.token == token))
    auth_token = result.scalar_one_or_none()
    if auth_token is not None:
        await session.delete(auth_token)
        await session.commit()
