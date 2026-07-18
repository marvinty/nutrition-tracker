from sqlalchemy import Column, Integer, String, DateTime, func
from app.models.base import Base


class SignupCode(Base):
    """Invite code handed out by an admin, valid for a limited number of signups.

    ``used_count`` is incremented by a conditional UPDATE at redemption time, so two
    people redeeming the last seat at once cannot both get in.
    """

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False, unique=True, index=True)
    label = Column(String, nullable=True)  # free text, e.g. which channel it went to
    max_uses = Column(Integer, nullable=False)
    used_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # null = no expiry
    revoked_at = Column(DateTime(timezone=True), nullable=True)  # null = still active
    created_by = Column(String, nullable=True)  # admin username, for the audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
