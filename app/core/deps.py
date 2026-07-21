from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User
from app.services.ai_log_service import set_ai_context
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
    # base.html reads this to decide whether to show the "confirm your address" banner,
    # which saves threading a flag through every page's context dict. It is deliberately
    # a plain value (the address, or None) rather than the User object: an error page can
    # render *after* the request session was rolled back — consume_credits does exactly
    # that on a 429 — and a rollback expires every ORM object on the session, so touching
    # user.email at render time would raise DetachedInstanceError and turn the intended
    # error page into a 500. Resolving it here, while the session is live, keeps the
    # template off the ORM. Always assigned, including the None case, so the template can
    # read it without guarding.
    request.state.verify_banner = None
    token = _extract_token(request)
    if not token:
        return None
    user = await get_user_by_token(session, token)
    if user is not None and user.email and not user.email_verified_at:
        request.state.verify_banner = user.email
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

    The app-wide ceiling counts *calls*, not the user-facing price, so an action priced
    at zero still costs one there. Otherwise a free action would be completely unmetered:
    the question limit that makes clarifying rounds finite lives in ``run_analysis`` and
    counts assistant turns in the *client-supplied* conversation, which bounds the app's
    own UI but not a caller posting a fresh one-message conversation every time.
    """
    cost = settings.credit_costs[action]
    global_cost = max(cost, 1)

    async def dependency(
        request: Request,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        await consume_credits(
            session,
            user.username,
            cost,
            limit_for(user.tier),
            global_limit=settings.global_daily_credits,
            global_cost=global_cost,
        )
        # Everything downstream of here may reach a provider, and the provider is
        # where the log row is written — but it cannot see who is calling. Setting
        # the context once here covers every AI endpoint, since each one already
        # depends on require_credits. Deliberately after the charge: a request
        # rejected for lack of credits never reaches an API and has nothing to log.
        set_ai_context(user.username, action, request.url.path)
        return user

    return dependency
