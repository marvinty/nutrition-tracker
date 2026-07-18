from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.models.base import Base


class AdminToken(Base):
    """Opaque admin session ticket. Kept in its own table (rather than a ``kind``
    on ``AuthToken``) so an admin token can never validate against
    ``get_user_by_token`` and vice versa."""

    token = Column(String, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("adminuser.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
