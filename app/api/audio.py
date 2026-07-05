from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user
from app.core.time import resolve_timestamp
from app.db.session import get_session
from app.models.user import User
from app.providers import get_provider
from app.providers.base import LLMProvider
from app.schemas.meal import AudioResponse, MealCreate
from app.services.audio_service import transcribe_audio
from app.services.meal_service import create_meal

router = APIRouter(prefix="/audio", tags=["audio"])


@router.post("", response_model=AudioResponse, status_code=201)
async def process_audio(
    file: UploadFile = File(...),
    log_date: Optional[date] = Form(None),
    session: AsyncSession = Depends(get_session),
    provider: LLMProvider = Depends(get_provider),
    user: User = Depends(get_current_user),
) -> AudioResponse:
    try:
        timestamp = resolve_timestamp(log_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        transcript = await transcribe_audio(audio_bytes, file.filename or "audio.wav")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Whisper transcription failed: {exc}") from exc

    try:
        nutrition = await provider.extract_nutrition(transcript)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {exc}") from exc

    meal = await create_meal(
        session,
        MealCreate(
            user_id=user.username,
            description=nutrition.description,
            calories=nutrition.calories,
            protein=nutrition.protein,
            carbs=nutrition.carbs,
            fat=nutrition.fat,
            timestamp=timestamp,
        ),
    )

    return AudioResponse(
        transcript=transcript,
        description=nutrition.description,
        calories=nutrition.calories,
        protein=nutrition.protein,
        carbs=nutrition.carbs,
        fat=nutrition.fat,
        meal_id=meal.id,
    )
