from sqlalchemy import Column, Integer, String, Date, UniqueConstraint
from app.models.base import Base


class VoiceUsage(Base):
    """Per-user daily counter of voice/transcription calls, for cost protection.

    One row per (user_id, day). ``day`` is the local calendar date
    (``settings.app_timezone``), so the limit resets at local midnight.
    """

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    day = Column(Date, nullable=False)
    count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_voice_usage_user_day"),
    )
