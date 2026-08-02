from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.time import today_local
from app.db.session import get_session
from app.models.user import User
from app.schemas.weight import WeightEntryCreate, WeightEntryRead
from app.services.weight_analysis import CHART_DAYS
from app.services.weight_service import (
    MAX_WEIGHT_KG,
    MIN_WEIGHT_KG,
    delete_entry,
    list_entries,
    upsert_entry,
)

# No require_credits anywhere in this router: nothing here reaches an LLM or
# Whisper, so there is nothing to meter.
router = APIRouter(prefix="/api/weight", tags=["weight"])


@router.post("", response_model=WeightEntryRead)
async def create_weight_entry(
    body: WeightEntryCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> WeightEntryRead:
    """Record a weigh-in. 200 rather than 201: it may well replace an existing day."""
    day = body.day or today_local()
    if day > today_local():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Datum darf nicht in der Zukunft liegen.",
        )
    if not MIN_WEIGHT_KG <= body.weight_kg <= MAX_WEIGHT_KG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Gewicht muss zwischen {MIN_WEIGHT_KG:.0f} und "
                f"{MAX_WEIGHT_KG:.0f} kg liegen."
            ),
        )
    entry = await upsert_entry(session, user.username, day, body.weight_kg)
    return WeightEntryRead.model_validate(entry)


@router.get("", response_model=list[WeightEntryRead])
async def read_weight_entries(
    start: Optional[date] = Query(default=None),
    end: Optional[date] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[WeightEntryRead]:
    today = today_local()
    end = end or today
    start = start or end - timedelta(days=CHART_DAYS - 1)
    entries = await list_entries(session, user.username, start, end)
    return [WeightEntryRead.model_validate(e) for e in entries]


@router.delete("/{day}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_weight_entry(
    day: date,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    if not await delete_entry(session, user.username, day):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kein Eintrag für dieses Datum.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
