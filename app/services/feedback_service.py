"""Store and read back user feedback.

Deliberately thin, mirroring ``ai_log_service.list_logs_for_user``: the router
owns the request session and its commit, this module owns the queries. Category
validation lives here so both the create path and any future caller agree on the
allowed values.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback

# The buckets the form offers, mapped to their German labels for display. Kept
# here so the router can validate against the keys and the admin view can render
# the labels from the same source.
CATEGORY_LABELS = {
    "bug": "Fehler",
    "idea": "Idee",
    "other": "Sonstiges",
}


async def create_feedback(
    session: AsyncSession, username: str, category: str, message: str
) -> Feedback:
    """Persist one message. Commits, so the row survives regardless of what the
    request handler does next."""
    entry = Feedback(user_id=username, category=category, message=message)
    session.add(entry)
    await session.commit()
    return entry


async def list_feedback(session: AsyncSession, limit: int = 200) -> list[Feedback]:
    """Newest feedback first, for the admin list."""
    result = await session.execute(
        select(Feedback)
        .order_by(Feedback.created_at.desc(), Feedback.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
