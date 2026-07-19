from sqlalchemy import Column, Integer, String, DateTime, func
from app.models.base import Base


class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    # The login identifier. Nullable only because SQLite cannot add a NOT NULL column
    # without a default to a table that already has rows — users predating email have
    # none. New accounts always get one; the registration route enforces that.
    email = Column(String, nullable=True, unique=True, index=True)
    # NULL means unconfirmed. After settings.email_verify_grace_minutes an account with
    # NULL here is locked out until it confirms — see auth_service.email_lock_state.
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Sets the daily AI credit budget (see settings.tier_daily_credits). No billing
    # yet, so this is assigned by hand: UPDATE user SET tier='pro' WHERE username=...
    tier = Column(String, nullable=False, server_default="free")
