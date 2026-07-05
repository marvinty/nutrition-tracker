from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User
from app.services.auth_service import get_user_by_token


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
