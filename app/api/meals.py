from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user
from app.core.time import resolve_timestamp
from app.db.session import get_session
from app.models.user import User
from app.providers import get_provider
from app.providers.base import LLMProvider
from app.schemas.meal import (
    ClarifyRequest,
    LogResponse,
    MealCreate,
    MealInput,
    MealRead,
    MealUpdate,
    TextMealCreate,
)
from app.services.meal_service import create_meal, delete_meal, list_meals, update_meal
from app.services.nutrition_flow import run_analysis

router = APIRouter(prefix="/meals", tags=["meals"])


def _timestamp_for(log_date) -> Optional[datetime]:
    try:
        return resolve_timestamp(log_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("", response_model=MealRead, status_code=201)
async def log_meal(
    body: MealInput,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> MealRead:
    fields = body.model_dump(exclude={"log_date"})
    meal = await create_meal(
        session,
        MealCreate(
            user_id=user.username,
            timestamp=_timestamp_for(body.log_date),
            **fields,
        ),
    )
    return meal


@router.post("/text", response_model=LogResponse)
async def log_meal_from_text(
    body: TextMealCreate,
    session: AsyncSession = Depends(get_session),
    provider: LLMProvider = Depends(get_provider),
    user: User = Depends(get_current_user),
) -> LogResponse:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")

    messages = [{"role": "user", "content": body.text}]
    try:
        return await run_analysis(provider, session, user, messages, body.log_date)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {exc}") from exc


@router.post("/clarify", response_model=LogResponse)
async def clarify_meal(
    body: ClarifyRequest,
    session: AsyncSession = Depends(get_session),
    provider: LLMProvider = Depends(get_provider),
    user: User = Depends(get_current_user),
) -> LogResponse:
    if not body.messages:
        raise HTTPException(status_code=400, detail="Conversation must not be empty")

    messages = [m.model_dump() for m in body.messages]
    try:
        return await run_analysis(provider, session, user, messages, body.log_date)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {exc}") from exc


@router.get("", response_model=list[MealRead])
async def get_meals(
    filter_date: Optional[date] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[MealRead]:
    return await list_meals(session, user_id=user.username, filter_date=filter_date)


@router.patch("/{meal_id}", response_model=MealRead)
async def edit_meal(
    meal_id: int,
    body: MealUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> MealRead:
    meal = await update_meal(session, meal_id, user.username, body)
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal not found")
    return meal


@router.delete("/{meal_id}", status_code=204)
async def remove_meal(
    meal_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    if not await delete_meal(session, meal_id, user.username):
        raise HTTPException(status_code=404, detail="Meal not found")
