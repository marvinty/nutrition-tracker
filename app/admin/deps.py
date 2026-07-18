from typing import Optional
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.services.admin_service import get_admin_by_token


async def resolve_admin(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Optional[AdminUser]:
    """Cookie only — unlike ``resolve_user`` there is no Bearer fallback, since the
    panel is browser-only and has no device/API clients to serve."""
    token = request.cookies.get(settings.admin_session_cookie_name)
    if not token:
        return None
    return await get_admin_by_token(session, token)
