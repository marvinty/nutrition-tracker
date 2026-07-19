"""Sliding-window throttling for the unauthenticated endpoints.

The credit limiter in ``usage_service`` cannot help here: it is keyed on a user and
needs an authenticated caller, which is exactly what an attacker guessing passwords
does not have. Without this, ``/login`` accepts password attempts as fast as the
network allows.

Two keys are counted for every sign-in attempt:

* the client IP, which stops one host working through a password list, and
* the account, which stops a botnet spreading that same list across many IPs — the
  case a per-IP limit alone misses completely.

Only *failures* are recorded, so a person using the app normally never approaches a
limit, and a successful login does not spend budget that a later typo might need.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.rate_limit import RateLimitHit

LOGIN = "login"
SIGNUP = "signup"
FORGOT_PASSWORD = "forgot_password"
ADMIN_LOGIN = "admin_login"

_DETAIL = (
    "Zu viele Versuche. Bitte warte {minutes} Minuten und probier es dann noch einmal."
)


def _utcnow() -> datetime:
    """Naive UTC, matching ``signup_code_service``.

    Timestamps are compared inside SQL WHERE clauses and SQLite returns naive values;
    mixing an aware ``now`` in raises as soon as SQLAlchemy evaluates the criteria.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ip_key(ip: str) -> str:
    return f"ip:{ip}"


def account_key(identifier: str) -> str:
    """Namespaced so an account literally named like an IP cannot share a bucket."""
    return f"account:{identifier.strip().lower()}"


def _limit_for(scope: str) -> int:
    return {
        LOGIN: settings.login_rate_limit,
        ADMIN_LOGIN: settings.login_rate_limit,
        SIGNUP: settings.signup_rate_limit,
        FORGOT_PASSWORD: settings.forgot_password_rate_limit,
    }.get(scope, settings.login_rate_limit)


async def count_hits(session: AsyncSession, scope: str, key: str) -> int:
    """Attempts recorded for ``key`` inside the current window."""
    cutoff = _utcnow() - timedelta(minutes=settings.login_rate_window_minutes)
    result = await session.execute(
        select(func.count())
        .select_from(RateLimitHit)
        .where(
            RateLimitHit.scope == scope,
            RateLimitHit.key == key,
            RateLimitHit.created_at > cutoff,
        )
    )
    return result.scalar_one()


async def record_hit(session: AsyncSession, scope: str, key: str) -> None:
    session.add(RateLimitHit(scope=scope, key=key, created_at=_utcnow()))
    await session.commit()


async def clear_hits(session: AsyncSession, scope: str, key: str) -> None:
    """Forget a key's failures. Called after a success, so someone who mistyped their
    password twice and then got it right starts the next window with a clean slate."""
    await session.execute(
        delete(RateLimitHit)
        .where(RateLimitHit.scope == scope, RateLimitHit.key == key)
        .execution_options(synchronize_session=False)
    )
    await session.commit()


async def enforce(
    session: AsyncSession, scope: str, *keys: Optional[str], limit: Optional[int] = None
) -> None:
    """Raise 429 if any of ``keys`` is over budget for ``scope``.

    Checking before doing the work — rather than only counting afterwards — is what
    makes this a limit rather than a statistic.
    """
    effective = _limit_for(scope) if limit is None else limit
    for key in keys:
        if key is None:
            continue
        if await count_hits(session, scope, key) >= effective:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=_DETAIL.format(minutes=settings.login_rate_window_minutes),
                headers={"Retry-After": str(settings.login_rate_window_minutes * 60)},
            )


async def record_failure(
    session: AsyncSession, scope: str, *keys: Optional[str]
) -> None:
    for key in keys:
        if key is not None:
            await record_hit(session, scope, key)


async def prune_expired(session: AsyncSession) -> int:
    """Drop rows outside the window. Called at startup so the table cannot grow
    unbounded across restarts; the window makes anything older meaningless anyway."""
    cutoff = _utcnow() - timedelta(minutes=settings.login_rate_window_minutes)
    result = await session.execute(
        delete(RateLimitHit)
        .where(RateLimitHit.created_at <= cutoff)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return result.rowcount
