from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.goal import GoalRead, GoalUpdate
from app.services.goal_service import get_goal, upsert_goal

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("", response_model=GoalRead)
async def read_goals(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GoalRead:
    goal = await get_goal(session, user.username)
    if goal is None:
        return GoalRead()
    return GoalRead.model_validate(goal)


@router.put("", response_model=GoalRead)
async def set_goals(
    body: GoalUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GoalRead:
    goal = await upsert_goal(session, user.username, body)
    return GoalRead.model_validate(goal)
