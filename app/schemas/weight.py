from datetime import date
from typing import Optional
from pydantic import BaseModel


class WeightEntryCreate(BaseModel):
    """A weigh-in. ``day`` defaults to today in the app timezone.

    Note the absence of ``Field(ge=..., le=...)`` on ``weight_kg``: Pydantic's
    validation error is English, and those ``detail`` strings are rendered to the
    user. The range is checked in the route so the message can be German, the same
    way ``api/meals.py`` converts a ValueError from ``resolve_timestamp``.
    """

    day: Optional[date] = None
    weight_kg: float


class WeightEntryRead(BaseModel):
    day: date
    weight_kg: float

    model_config = {"from_attributes": True}
