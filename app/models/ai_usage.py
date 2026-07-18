from sqlalchemy import Column, Integer, String, Date, UniqueConstraint
from app.models.base import Base


class AiUsage(Base):
    """Per-user daily credit counter covering every cost-incurring AI call.

    One row per (user_id, day). ``count`` is the sum of credits spent, not a call
    count: each action has a price in ``settings.credit_costs`` (voice costs more
    than text because it pays for transcription *and* the LLM analysis). ``day``
    is the local calendar date (``settings.app_timezone``), so the quota resets at
    local midnight.
    """

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    day = Column(Date, nullable=False)
    count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_ai_usage_user_day"),
    )
