from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User
from app.services.auth_service import get_user_by_token, is_locked_for_unverified_email
from app.services.usage_service import consume_credits, limit_for

# The only paths an account with a lapsed, unconfirmed address may still reach. Without
# them the lock would be a dead end: no way to request a new mail, no way to confirm the
# one already sent, no way to sign out and use a different account.
_LOCK_EXEMPT_PATHS = frozenset(
    {
        "/verify-email",
        "/verify-email/required",
        "/verify-email/resend",
        "/logout",
        "/login",
        "/register",
        "/forgot-password",
        "/reset-password",
    }
)


class EmailVerificationRequired(Exception):
    """Raised when a locked account touches anything outside the exempt paths.

    Carried out to an exception handler rather than returned inline because it is
    raised from a dependency, which has no response to return. The handler decides
    between a redirect and a 403 based on what the caller asked for.
    """


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
    # Templates read this to decide whether to show the "confirm your address" banner,
    # which saves threading a flag through every page's context dict. Always assigned,
    # including the None case, so a template can access it without guarding.
    request.state.user = None
    token = _extract_token(request)
    if not token:
        return None
    user = await get_user_by_token(session, token)
    request.state.user = user
    if (
        user is not None
        and request.url.path not in _LOCK_EXEMPT_PATHS
        and is_locked_for_unverified_email(user)
    ):
        raise EmailVerificationRequired()
    return user


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
