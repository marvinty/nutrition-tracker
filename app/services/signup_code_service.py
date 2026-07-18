"""Invite codes: creation, listing and redemption.

Redemption is the delicate part — see ``redeem_code`` for why it is a single
conditional UPDATE rather than a read-then-write.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.signup_code import SignupCode
from app.services.auth_service import signup_code_ok
from app.services.settings_service import is_signup_closed

# No I/O/0/1: these codes get read aloud, typed off a phone screen and pasted from
# chat messages, and those four are where transcription errors come from.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 8


def _utcnow() -> datetime:
    """Current UTC time as a *naive* datetime.

    Unlike the token tables, expiry here is compared inside a SQL WHERE clause. SQLite
    stores no offset and hands values back naive, so mixing in an aware ``now`` raises
    "can't compare offset-naive and offset-aware datetimes" as soon as SQLAlchemy
    evaluates the criteria in Python. Keeping both sides naive UTC — on write and on
    read — sidesteps that entirely.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))


@dataclass
class CodeRow:
    """One row of the admin invite-code list, with its status pre-computed."""

    id: int
    code: str
    label: Optional[str]
    max_uses: int
    used_count: int
    remaining: int
    expires_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]
    status: str  # "active" | "used_up" | "expired" | "revoked"


def _status_of(c: SignupCode, now: datetime) -> str:
    if c.revoked_at is not None:
        return "revoked"
    if c.used_count >= c.max_uses:
        return "used_up"
    expires_at = c.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is not None:  # normalise to the naive UTC `now` we compare against
            expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)
        if expires_at <= now:
            return "expired"
    return "active"


async def create_code(
    session: AsyncSession,
    *,
    max_uses: int,
    label: Optional[str] = None,
    valid_days: Optional[int] = None,
    created_by: Optional[str] = None,
) -> SignupCode:
    """Mint a new invite code good for ``max_uses`` signups."""
    if max_uses < 1:
        raise ValueError("max_uses must be at least 1")
    expires_at = (
        _utcnow() + timedelta(days=valid_days)
        if valid_days is not None and valid_days > 0
        else None
    )
    code = SignupCode(
        code=generate_code(),
        label=(label or "").strip() or None,
        max_uses=max_uses,
        used_count=0,
        expires_at=expires_at,
        created_by=created_by,
    )
    session.add(code)
    await session.commit()
    await session.refresh(code)
    return code


async def list_codes(session: AsyncSession) -> list[CodeRow]:
    """All codes, newest first, with status resolved for display."""
    # populate_existing: the counter updates above run with synchronize_session=False,
    # so the session's cached copies can be stale. Without this the panel could show a
    # code as still available right after someone used its last seat.
    result = await session.execute(
        select(SignupCode)
        .order_by(SignupCode.created_at.desc())
        .execution_options(populate_existing=True)
    )
    now = _utcnow()
    return [
        CodeRow(
            id=c.id,
            code=c.code,
            label=c.label,
            max_uses=c.max_uses,
            used_count=c.used_count,
            remaining=max(c.max_uses - c.used_count, 0),
            expires_at=c.expires_at,
            revoked_at=c.revoked_at,
            created_at=c.created_at,
            created_by=c.created_by,
            status=_status_of(c, now),
        )
        for c in result.scalars().all()
    ]


async def revoke_code(session: AsyncSession, code_id: int) -> bool:
    """Disable a code immediately. Returns False if it was already revoked or gone."""
    result = await session.execute(
        update(SignupCode)
        .where(SignupCode.id == code_id, SignupCode.revoked_at.is_(None))
        .values(revoked_at=_utcnow())
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return result.rowcount == 1


async def redeem_code(session: AsyncSession, provided: str) -> bool:
    """Consume one seat of ``provided``, returning whether it was valid.

    The whole check lives in the UPDATE's WHERE clause rather than in a read followed
    by a write: a code with one seat left could otherwise be validated by two
    concurrent registrations before either increments the counter, and both would get
    in. Here the database decides, and ``rowcount`` tells us who won.
    """
    code = provided.strip().upper()
    if not code:
        return False
    result = await session.execute(
        update(SignupCode)
        .where(
            SignupCode.code == code,
            SignupCode.revoked_at.is_(None),
            SignupCode.used_count < SignupCode.max_uses,
            or_(SignupCode.expires_at.is_(None), SignupCode.expires_at > _utcnow()),
        )
        .values(used_count=SignupCode.used_count + 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        # Nothing matched, so nothing was changed and there is nothing to roll back.
        # Rolling back here would expire every object in the caller's session and
        # discard any unrelated pending work in the same request.
        return False
    await session.commit()
    return True


async def refund_code(session: AsyncSession, provided: str) -> None:
    """Give back a seat taken by ``redeem_code`` when the signup did not complete.

    A no-op for the environment code and for anything that never matched a row, so the
    caller can pass whatever the user typed. ``used_count > 0`` guards against a refund
    pushing the counter negative if this is ever called twice.
    """
    code = provided.strip().upper()
    if not code:
        return
    await session.execute(
        update(SignupCode)
        .where(SignupCode.code == code, SignupCode.used_count > 0)
        .values(used_count=SignupCode.used_count - 1)
        .execution_options(synchronize_session=False)
    )
    await session.commit()


async def signup_requires_code(session: AsyncSession) -> bool:
    """Whether the registration form must ask for a code.

    Two independent switches, either of which closes signup: the panel toggle, and
    ``SIGNUP_CODE`` from the environment (kept from before the panel existed).
    """
    if settings.signup_code:
        return True
    return await is_signup_closed(session)


async def signup_allowed(session: AsyncSession, provided: str) -> bool:
    """Whether registration with ``provided`` may proceed, consuming a seat if it does.

    The environment code is checked first and is never consumed: it is the break-glass
    path for when the panel itself is unreachable, so it must not be able to run out.
    """
    if not await signup_requires_code(session):
        return True
    if settings.signup_code and signup_code_ok(provided):
        return True
    return await redeem_code(session, provided)
