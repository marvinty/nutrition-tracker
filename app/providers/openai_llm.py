from openai import AsyncOpenAI
from app.providers.base import (
    AnalysisResult,
    LLMProvider,
    build_system_prompt,
    parse_analysis,
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
