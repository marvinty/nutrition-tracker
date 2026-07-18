"""Per-user and app-wide daily credit limiting for the AI endpoints.

LLM extraction and Whisper transcription are the app's variable costs, so every
endpoint that triggers one spends credits from a daily budget. Actions are weighted
(see ``settings.credit_costs``) and the per-user budget depends on the user's tier
(``settings.tier_daily_credits``), which is what makes free vs. pro possible.

On top of that sits an app-wide ceiling (``settings.global_daily_credits``), tracked
as one more row under ``GLOBAL_KEY``. Per-user limits alone cannot stop a burst of
new signups or a runaway client loop, so the global one is the actual circuit breaker
against a surprise bill. It is meant to sit well above normal usage: if it ever trips,
something is wrong, and everyone is locked out until local midnight.
"""
from typing import NamedTuple, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.time import today_local
from app.models.ai_usage import AiUsage

# Sentinel user_id for the app-wide counter. Usernames are unique, and the leading
# underscores keep it from colliding with a real one.
GLOBAL_KEY = "__global__"

_USER_LIMIT_DETAIL = "Tägliches Limit erreicht ({limit} Credits). Morgen wieder verfügbar."
# Deliberately different wording: it tells the user it is not their fault, and it
# makes the two cases distinguishable in the logs.
_GLOBAL_LIMIT_DETAIL = (
    "Systemlimit für heute erreicht. Das liegt nicht an deinem Konto — "
    "bitte versuch es morgen wieder."
)


class CreditStatus(NamedTuple):
    """What a user has left today, plus whether the app-wide ceiling still allows work."""

    used: int
    limit: int
    remaining: int
    tier: str
    system_available: bool


async def get_usage(session: AsyncSession, user_id: str) -> int:
    """Credits ``user_id`` has spent today. Zero if they haven't used the app yet."""
    result = await session.execute(
        select(AiUsage).where(AiUsage.user_id == user_id, AiUsage.day == today_local())
    )
    usage = result.scalar_one_or_none()
    return usage.count if usage is not None else 0


def limit_for(tier: str) -> int:
    """Daily credit budget for ``tier``, falling back to free for an unknown one."""
    limits = settings.tier_daily_credits
    return limits.get(tier, limits["free"])


async def get_credit_status(
    session: AsyncSession, user_id: str, tier: str
) -> CreditStatus:
    """Everything the UI needs to explain today's budget.

    ``system_available`` is false once the app-wide ceiling is spent, which is worth
    surfacing separately: the user may still have personal credits left and would
    otherwise see a full budget and an unexplained 429.
    """
    used = await get_usage(session, user_id)
    limit = limit_for(tier)
    global_used = await get_usage(session, GLOBAL_KEY)
    return CreditStatus(
        used=used,
        limit=limit,
        remaining=max(limit - used, 0),
        tier=tier,
        system_available=global_used < settings.global_daily_credits,
    )


async def _reserve(
    session: AsyncSession, user_id: str, cost: int, limit: int, detail: str
) -> int:
    """Add ``cost`` to one counter, or raise 429. Does not commit — the caller does.

    Rejects an action the remaining budget cannot cover outright rather than letting it
    overdraw, so a user with 2 credits left cannot start a 3-credit voice log.
    """
    day = today_local()
    result = await session.execute(
        select(AiUsage).where(AiUsage.user_id == user_id, AiUsage.day == day)
    )
    usage = result.scalar_one_or_none()

    current = usage.count if usage is not None else 0
    if current + cost > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail
        )

    if usage is None:
        usage = AiUsage(user_id=user_id, day=day, count=cost)
        session.add(usage)
    else:
        usage.count = current + cost
    return current + cost


async def consume_credits(
    session: AsyncSession,
    user_id: str,
    cost: int,
    limit: int,
    global_limit: Optional[int] = None,
) -> int:
    """Spend ``cost`` credits for ``user_id`` today, raising 429 if either budget is out.

    Both counters move in a single transaction, so a request rejected by the second
    check does not leave the first one charged — without the rollback the global
    increment would linger in the session and ride along on the next commit, letting
    one user drain the shared ceiling with requests that were all refused. Returns the
    user's new total. The day is the local calendar date, so budgets reset at local
    midnight. ``global_limit`` of ``None`` skips the app-wide ceiling.
    """
    try:
        if global_limit is not None:
            await _reserve(session, GLOBAL_KEY, cost, global_limit, _GLOBAL_LIMIT_DETAIL)
        total = await _reserve(
            session, user_id, cost, limit, _USER_LIMIT_DETAIL.format(limit=limit)
        )
    except HTTPException:
        await session.rollback()
        raise
    await session.commit()
    return total
