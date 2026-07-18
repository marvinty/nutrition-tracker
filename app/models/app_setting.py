from sqlalchemy import Column, String, DateTime, func
from app.models.base import Base


class AppSetting(Base):
    """Key/value store for settings an admin can flip at runtime.

    Deliberately separate from ``app.core.config.Settings``: those come from the
    environment and need a restart, these are changed from the panel and take effect
    immediately. Values are stored as strings; typed accessors live in
    ``app.services.settings_service``.
    """

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
