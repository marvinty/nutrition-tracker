from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User
from app.services.auth_service import get_user_by_token
from app.services.usage_service import consume_credits, limit_for


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


def require_credits(action: str):
    """Build a ``get_current_user`` variant that also charges the user for ``action``.

    ``action`` keys into ``settings.credit_costs``. The dependency raises 429 once either
    the user's daily budget (from their tier) or the app-wide ceiling is exhausted, so it
    belongs on every endpoint that reaches an LLM or Whisper. Charging happens before the
    work, which means a failed call still costs a credit — acceptable, since the API call
    is usually already paid for by then.
    """
    cost = settings.credit_costs[action]

    async def dependency(
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        await consume_credits(
            session,
            user.username,
            cost,
            limit_for(user.tier),
            global_limit=settings.global_daily_credits,
        )
        return user

    return dependency
