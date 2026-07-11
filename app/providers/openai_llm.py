from openai import AsyncOpenAI
from app.providers.base import (
    AnalysisResult,
    LLMProvider,
    NutritionResult,
    build_ingredients_prompt,
    build_system_prompt,
    parse_analysis,
    parse_ingredients,
)
from app.core.config import settings


class OpenAILLMProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def analyze(
        self, messages: list[dict], allow_questions: bool
    ) -> AnalysisResult:
        response = await self._client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=256,
            messages=[
                {"role": "system", "content": build_system_prompt(allow_questions)},
                *messages,
            ],
        )
        raw = response.choices[0].message.content or ""
        return parse_analysis(raw, messages, allow_questions)

    async def extract_ingredients(self, text: str) -> list[NutritionResult]:
        response = await self._client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=512,
            messages=[
                {"role": "system", "content": build_ingredients_prompt()},
                {"role": "user", "content": text},
            ],
        )
        raw = response.choices[0].message.content or ""
        return parse_ingredients(raw, text)
