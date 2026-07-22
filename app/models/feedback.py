from sqlalchemy import Column, DateTime, Integer, String, Text, func
from app.models.base import Base


class Feedback(Base):
    """One row per piece of feedback a logged-in user sends us.

    Kept in the database rather than mailed out for the same reasons the AI log
    is: it is searchable, it is tied to the user who wrote it, and it does not
    get lost in an inbox. Reachable only from the admin panel.
    """

    id = Column(Integer, primary_key=True, index=True)
    # Username, matching the Meal/AiRequestLog convention — a String, not a FK to
    # user.id. Not nullable: feedback is a logged-in-only feature, so every row
    # has an author.
    user_id = Column(String, nullable=False, index=True)
    # Coarse bucket chosen in the form: "bug" | "idea" | "other". Indexed so the
    # admin list can later be filtered by it without a scan.
    category = Column(String, nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
