from sqlalchemy import Column, Integer, String, DateTime, func
from app.models.base import Base


class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Sets the daily AI credit budget (see settings.tier_daily_credits). No billing
    # yet, so this is assigned by hand: UPDATE user SET tier='pro' WHERE username=...
    tier = Column(String, nullable=False, server_default="free")
