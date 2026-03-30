from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.providers import get_provider
from app.providers.base import LLMProvider
from app.schemas.meal import AudioResponse, MealCreate
from app.services.audio_service import transcribe_audio
from app.services.meal_service import create_meal

router = APIRouter(prefix="/audio", tags=["audio"])


@router.post("", response_model=AudioResponse, status_code=201)
async def process_audio(
    file: UploadFile = File(...),
    user_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_session),
    provider: LLMProvider = Depends(get_provider),
) -> AudioResponse:
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
            user_id=user_id,
            description=nutrition.description,
            calories=nutrition.calories,
            protein=nutrition.protein,
            carbs=nutrition.carbs,
            fat=nutrition.fat,
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
