from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.models.base import Base


class AuthToken(Base):
    """Opaque logon ticket. Usable both as a browser session cookie and as a
    device/API bearer token, so API calls can be attributed to a user."""

    token = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    kind = Column(String, nullable=False, default="session")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
