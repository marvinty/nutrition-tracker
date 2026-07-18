from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.usage import UsageRead
from app.services.usage_service import get_credit_status

# /api/... like the other browser-only endpoints (goals, recipes); /meals and /audio
# sit at the root because the ESP32 client calls them.
router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("", response_model=UsageRead)
async def read_usage(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> UsageRead:
    """Today's credit budget, so users see the limit coming instead of hitting a 429."""
    status = await get_credit_status(session, user.username, user.tier)
    return UsageRead.model_validate(status._asdict())
