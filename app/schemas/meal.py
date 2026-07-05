from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TextMealCreate(BaseModel):
    text: str


class MealInput(BaseModel):
    description: str
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None


class MealCreate(BaseModel):
    description: str
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    user_id: str


class MealRead(BaseModel):
    id: int
    user_id: str
    description: str
    calories: Optional[float]
    protein: Optional[float]
    carbs: Optional[float]
    fat: Optional[float]
    timestamp: datetime

    model_config = {"from_attributes": True}


class AudioResponse(BaseModel):
    transcript: str
    description: str
    calories: Optional[float]
    protein: Optional[float]
    carbs: Optional[float]
    fat: Optional[float]
    meal_id: int
