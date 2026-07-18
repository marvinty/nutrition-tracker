from sqlalchemy import Column, Integer, String, DateTime, func
from app.models.base import Base


class AdminUser(Base):
    """Panel operator. Deliberately a separate table from ``User`` rather than a
    flag on it: an app user can never accidentally gain admin rights, and a stolen
    user session grants no access to /admin."""

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
