from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import resolve_timestamp
from app.models.user import User
from app.providers.base import ClarificationNeeded, LLMProvider
from app.schemas.meal import ConversationMessage, LogResponse, MealCreate, MealRead
from app.services.meal_service import create_meal

MAX_QUESTIONS = 2


async def run_analysis(
    provider: LLMProvider,
    session: AsyncSession,
    user: User,
    messages: list[dict],
    log_date: Optional[date],
    transcript: Optional[str] = None,
) -> LogResponse:
    """Run one analysis turn over the conversation so far.

    Returns a clarifying question (without saving) while the model still needs
    info and we are under the question limit; otherwise estimates and saves the
    meal. After MAX_QUESTIONS assistant turns, the model is forced to estimate.
    """
    assistant_turns = sum(1 for m in messages if m.get("role") == "assistant")
    allow_questions = assistant_turns < MAX_QUESTIONS

    result = await provider.analyze(messages, allow_questions)

    if isinstance(result, ClarificationNeeded):
        messages = messages + [{"role": "assistant", "content": result.question}]
        return LogResponse(
            status="needs_clarification",
            question=result.question,
            messages=[ConversationMessage(**m) for m in messages],
            transcript=transcript,
        )

    try:
        timestamp = resolve_timestamp(log_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    meal = await create_meal(
        session,
        MealCreate(
            user_id=user.username,
            description=result.description,
            calories=result.calories,
            protein=result.protein,
            carbs=result.carbs,
            fat=result.fat,
            timestamp=timestamp,
        ),
    )
    return LogResponse(
        status="complete",
        meal=MealRead.model_validate(meal),
        transcript=transcript,
    )
