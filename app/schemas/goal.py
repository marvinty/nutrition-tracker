from typing import Optional
from pydantic import BaseModel, Field


class GoalUpdate(BaseModel):
    calories: Optional[float] = Field(default=None, ge=0)
    protein: Optional[float] = Field(default=None, ge=0)
    carbs: Optional[float] = Field(default=None, ge=0)
    fat: Optional[float] = Field(default=None, ge=0)
    # Not ge=0, unlike every macro above it: a cut is a *negative* rate, and the
    # house style would silently make this field useless for anyone losing weight.
    # The bounds double as the sanity clamp — nobody targets 1.5 kg a week.
    weekly_change_kg: Optional[float] = Field(default=None, ge=-1.5, le=1.5)


class GoalRead(BaseModel):
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    weekly_change_kg: Optional[float] = None

    model_config = {"from_attributes": True}
