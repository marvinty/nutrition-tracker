from sqlalchemy import Column, Integer, String

from app.models.base import Base


class UserTokenTotal(Base):
    """Cumulative lifetime token spend per user, one row per user_id.

    Deliberately separate from ``AiRequestLog``: those rows carry the tokens of a
    single call but are pruned after ``ai_log_retention_days``, so a sum over them
    only ever covers the retention window. This counter is incremented as each call
    is logged and never pruned, so it answers "how many tokens has this user used in
    total" for real. ``prompt_tokens`` is input, ``completion_tokens`` output —
    mirroring the columns on ``AiRequestLog``. Transcription and failed calls carry
    no token counts and leave this untouched.
    """

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, unique=True, index=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
