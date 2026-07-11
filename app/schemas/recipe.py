from datetime import date
from typing import Optional
from pydantic import BaseModel


class RecipeCreate(BaseModel):
    name: str
    servings: int = 1


class RecipeUpdate(BaseModel):
    # Also the building block for later voice-driven recipe editing.
    name: Optional[str] = None
    servings: Optional[int] = None


class IngredientTextInput(BaseModel):
    text: str


class RecipeIngredientRead(BaseModel):
    id: int
    description: str
    calories: Optional[float]
    protein: Optional[float]
    carbs: Optional[float]
    fat: Optional[float]

    model_config = {"from_attributes": True}


class Macros(BaseModel):
    calories: float
    protein: float
    carbs: float
    fat: float


class RecipeRead(BaseModel):
    id: int
    name: str
    servings: int
    ingredients: list[RecipeIngredientRead]
    total: Macros
    per_portion: Macros

    model_config = {"from_attributes": True}


class LogPortionRequest(BaseModel):
    portions: float = 1
    log_date: Optional[date] = None
