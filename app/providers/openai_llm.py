import json
import re
from openai import AsyncOpenAI
from app.providers.base import LLMProvider, NutritionResult
from app.core.config import settings

SYSTEM_PROMPT = """You are a nutrition analysis assistant.
The user will describe food they have eaten (typed or transcribed from speech).
Extract: description, calories, protein, carbs, fat.
Respond ONLY with a valid JSON object using these exact keys:
{
  "description": "...",
  "calories": 0.0,
  "protein": 0.0,
  "carbs": 0.0,
  "fat": 0.0
}
If a value cannot be determined, use null.
Do not include any text outside the JSON object."""


class OpenAILLMProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract_nutrition(self, transcript: str) -> NutritionResult:
        response = await self._client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=256,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
        )
        raw = response.choices[0].message.content or ""
        cleaned = re.sub(r"```json?\s*|\s*```", "", raw).strip()
        data = json.loads(cleaned)
        return NutritionResult(
            description=data.get("description", transcript),
            calories=data.get("calories"),
            protein=data.get("protein"),
            carbs=data.get("carbs"),
            fat=data.get("fat"),
        )
