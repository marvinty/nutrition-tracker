from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.models.base import Base


class MacroGoal(Base):
    """Per-user daily macro targets. One row per user (unique user_id).

    Each target is nullable so a user can set, e.g., only a protein goal.

    ``weekly_change_kg`` is the rate of body-weight change the user is aiming for:
    positive = Aufbau, negative = Abnehmen, 0 = halten, NULL = kein Ziel-Tempo
    genannt. Note that 0 and NULL mean different things here, so every read must
    use ``is not None`` rather than truthiness. It is a pure *input* to the
    suggestion on /weight — nothing ever derives ``calories`` from it.
    """

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, unique=True, index=True)
    calories = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    weekly_change_kg = Column(Float, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
