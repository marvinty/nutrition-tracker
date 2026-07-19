from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import (
    generate_token,
    hash_password,
    normalize_email,
    validate_password,
    verify_password,
)
from app.models.auth_token import AuthToken
from app.models.user import User

# AuthToken.kind values. Session tokens ride in the cookie; the other two are
# single-purpose tickets that travel in an email link and must never be usable as a
# session — see ``get_user_by_token``.
SESSION_TOKEN = "session"
VERIFY_TOKEN = "verify"
RESET_TOKEN = "reset"

# A verification link should survive a mail client sitting on it overnight; a reset link
# is a live credential and gets no such courtesy.
VERIFY_TTL = timedelta(hours=24)
RESET_TTL = timedelta(hours=1)


def _as_utc(value: datetime) -> datetime:
    """Read a stored timestamp as aware UTC. SQLite hands back naive values."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class UsernameTakenError(Exception):
    """Raised when trying to create a user whose username already exists."""


class EmailTakenError(Exception):
    """Raised when trying to create a user whose email already exists."""


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession, username: str, email: str, password: str
) -> User:
    """Create an account. ``email`` must already be normalized by the caller.

    Password rules live here rather than in the router so no future caller can set a
    password that bypasses them.
    """
    validate_password(password)
    existing = await session.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none() is not None:
        raise UsernameTakenError(username)
    if await get_user_by_email(session, email) is not None:
        raise EmailTakenError(email)
    user = User(username=username, email=email, password_hash=hash_password(password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(
    session: AsyncSession, email: str, password: str
) -> Optional[User]:
    """Verify credentials against the email identifier.

    A malformed address is simply wrong credentials — telling the user their input was
    not email-shaped adds nothing on a login form.
    """
    try:
        email = normalize_email(email)
    except ValueError:
        return None
    user = await get_user_by_email(session, email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def is_email_verified(user: User) -> bool:
    return user.email_verified_at is not None


def is_locked_for_unverified_email(user: User) -> bool:
    """Whether ``user`` must confirm their address before using the app again.

    Unverified accounts stay usable for a grace period so signup is not gated on mail
    delivery; once it lapses, the account is frozen rather than deleted, and confirming
    at any later point thaws it.
    """
    if is_email_verified(user):
        return False
    grace = timedelta(minutes=settings.email_verify_grace_minutes)
    return _as_utc(user.created_at) + grace < datetime.now(timezone.utc)


async def create_token(
    session: AsyncSession, user: User, kind: str = SESSION_TOKEN
) -> AuthToken:
    ttl = {
        VERIFY_TOKEN: VERIFY_TTL,
        RESET_TOKEN: RESET_TTL,
    }.get(kind, timedelta(days=settings.session_ttl_days))
    token = AuthToken(
        token=generate_token(),
        user_id=user.id,
        kind=kind,
        expires_at=datetime.now(timezone.utc) + ttl,
    )
    session.add(token)
    await session.commit()
    return token


async def get_user_by_token(
    session: AsyncSession, token: str, kind: str = SESSION_TOKEN
) -> Optional[User]:
    """Resolve ``token`` of exactly ``kind`` to its user, or None.

    Matching on ``kind`` is what keeps the shared token table honest. Without it the
    confirmation link mailed to a new user would authenticate as a session cookie, so
    anyone who saw that URL — in a forwarded mail, a proxy log, a Referer header — would
    hold a 30-day login for that account.
    """
    result = await session.execute(
        select(AuthToken).where(AuthToken.token == token, AuthToken.kind == kind)
    )
    auth_token = result.scalar_one_or_none()
    if auth_token is None:
        return None
    if auth_token.expires_at is not None:
        if _as_utc(auth_token.expires_at) < datetime.now(timezone.utc):
            return None
    result = await session.execute(select(User).where(User.id == auth_token.user_id))
    return result.scalar_one_or_none()


async def latest_token_created_at(
    session: AsyncSession, user: User, kind: str
) -> Optional[datetime]:
    """When ``user`` last got a token of ``kind``. Used to throttle re-sends."""
    result = await session.execute(
        select(AuthToken.created_at)
        .where(AuthToken.user_id == user.id, AuthToken.kind == kind)
        .order_by(AuthToken.created_at.desc())
        .limit(1)
    )
    created_at = result.scalar_one_or_none()
    return _as_utc(created_at) if created_at is not None else None


async def delete_user_tokens(
    session: AsyncSession, user: User, kind: Optional[str] = None
) -> None:
    """Drop ``user``'s tokens, of one kind or all of them."""
    stmt = delete(AuthToken).where(AuthToken.user_id == user.id)
    if kind is not None:
        stmt = stmt.where(AuthToken.kind == kind)
    await session.execute(stmt.execution_options(synchronize_session=False))
    await session.commit()


async def mark_email_verified(session: AsyncSession, user: User) -> None:
    """Confirm the address and drop the outstanding verification tokens."""
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
        await session.commit()
    await delete_user_tokens(session, user, VERIFY_TOKEN)


def signup_code_ok(provided: str) -> bool:
    """Whether ``provided`` unlocks registration.

    An empty ``settings.signup_code`` means signup is open (dev default); the app logs
    a warning at startup so that is a choice rather than an accident.
    """
    if not settings.signup_code:
        return True
    return provided.strip() == settings.signup_code


async def reset_password(session: AsyncSession, user: User, password: str) -> None:
    """Set a new password and invalidate everything the old one could reach.

    Dropping *all* tokens — sessions included — is the point of a reset: someone who
    lost control of the account needs the other party logged out, not just locked out of
    changing the password. Reaching the reset link also proves control of the mailbox,
    so it doubles as verification for an address that never got confirmed.
    """
    validate_password(password)
    user.password_hash = hash_password(password)
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
    await session.commit()
    await delete_user_tokens(session, user)


async def delete_token(session: AsyncSession, token: str) -> None:
    result = await session.execute(select(AuthToken).where(AuthToken.token == token))
    auth_token = result.scalar_one_or_none()
    if auth_token is not None:
        await session.delete(auth_token)
        await session.commit()
