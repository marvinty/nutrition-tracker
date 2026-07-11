"""Per-user daily usage limiting for the voice/transcription endpoints.

Whisper transcription is the app's main variable cost (OpenAI ~$0.02/min, or CPU
for the local model). This caps how many voice calls a single user can make per
local calendar day, as cost protection before any public test.
"""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import today_local
from app.models.voice_usage import VoiceUsage


async def check_and_increment_voice(
    session: AsyncSession, user_id: str, limit: int
) -> int:
    """Reserve one voice call for ``user_id`` today, or reject if over ``limit``.

    Raises ``HTTPException`` (429) when the user has already used ``limit`` calls
    today. Otherwise increments the counter and returns the new count. The day is
    the local calendar date, so the quota resets at local midnight.
    """
    day = today_local()
    result = await session.execute(
        select(VoiceUsage).where(
            VoiceUsage.user_id == user_id, VoiceUsage.day == day
        )
    )
    usage = result.scalar_one_or_none()

    current = usage.count if usage is not None else 0
    if current >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Tägliches Voice-Limit erreicht ({limit}). Morgen wieder verfügbar.",
        )

    if usage is None:
        usage = VoiceUsage(user_id=user_id, day=day, count=1)
        session.add(usage)
    else:
        usage.count = current + 1
    await session.commit()
    return current + 1
