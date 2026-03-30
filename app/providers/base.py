from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class NutritionResult:
    description: str
    calories: Optional[float]
    protein: Optional[float]
    carbs: Optional[float]
    fat: Optional[float]


class LLMProvider(ABC):
    @abstractmethod
    async def extract_nutrition(self, transcript: str) -> NutritionResult:
        """
        Given a free-text food description (from speech-to-text or typed),
        return structured nutrition data.
        """
        ...
