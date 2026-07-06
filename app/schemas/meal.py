from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel


class TextMealCreate(BaseModel):
    text: str
    log_date: Optional[date] = None


class MealInput(BaseModel):
    description: str
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    log_date: Optional[date] = None


class MealCreate(BaseModel):
    description: str
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    user_id: str
    timestamp: Optional[datetime] = None


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


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ClarifyRequest(BaseModel):
    messages: list[ConversationMessage]
    log_date: Optional[date] = None


class LogResponse(BaseModel):
    status: Literal["complete", "needs_clarification"]
    question: Optional[str] = None
    # Full conversation so far, including the latest assistant question.
    messages: list[ConversationMessage] = []
    meal: Optional[MealRead] = None
    transcript: Optional[str] = None  # only set on the first /audio call
