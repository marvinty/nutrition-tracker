from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User
from app.services.auth_service import get_user_by_token
from app.services.usage_service import check_and_increment_voice


def _extract_token(request: Request) -> Optional[str]:
    """Cookie (browser) takes precedence, then Authorization: Bearer (device/API)."""
    cookie_token = request.cookies.get(settings.session_cookie_name)
    if cookie_token:
        return cookie_token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer ") :].strip() or None
    return None


async def resolve_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    token = _extract_token(request)
    if not token:
        return None
    return await get_user_by_token(session, token)


async def get_current_user(user: Optional[User] = Depends(resolve_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def enforce_voice_quota(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Like ``get_current_user`` but also counts the call against the user's daily
    voice quota, raising 429 when exceeded. Use on the transcription endpoints."""
    await check_and_increment_voice(session, user.username, settings.voice_daily_limit)
    return user
