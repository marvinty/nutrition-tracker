from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint, func
from app.models.base import Base


class WeightEntry(Base):
    """One weigh-in per user and calendar day.

    ``day`` is the local calendar date (``settings.app_timezone``), not a timestamp:
    a weigh-in belongs to a day, and the smoothing works on days. The unique
    constraint is load-bearing rather than hygiene — the 7-day average assumes at
    most one point per day, so a second entry for the same day replaces the first.

    ``user_id`` is the username, matching the Meal/MacroGoal convention — a String,
    not a FK to user.id.
    """

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    day = Column(Date, nullable=False)
    weight_kg = Column(Float, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_weight_entry_user_day"),
    )
