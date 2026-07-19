from typing import Optional

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
from app.services.ai_log_service import log_ai_call, serialize_prompt

_MODEL = "gpt-4o-mini"


def _usage(response) -> tuple[Optional[int], Optional[int]]:
    """Token counts, or a pair of Nones — ``usage`` is optional on the response."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return None, None
    return usage.prompt_tokens, usage.completion_tokens


class OpenAILLMProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def analyze(
        self, messages: list[dict], allow_questions: bool
    ) -> AnalysisResult:
        system = build_system_prompt(allow_questions)
        async with log_ai_call(
            kind="llm_analyze", provider="openai", model=_MODEL
        ) as rec:
            rec.set_prompt(serialize_prompt(system, messages))
            response = await self._client.chat.completions.create(
                model=_MODEL,
                max_tokens=256,
                messages=[{"role": "system", "content": system}, *messages],
            )
            raw = response.choices[0].message.content or ""
            tokens_in, tokens_out = _usage(response)
            rec.set_response(raw, tokens_in=tokens_in, tokens_out=tokens_out)
        return parse_analysis(raw, messages, allow_questions)

    async def extract_ingredients(self, text: str) -> list[NutritionResult]:
        system = build_ingredients_prompt()
        messages = [{"role": "user", "content": text}]
        async with log_ai_call(
            kind="llm_ingredients", provider="openai", model=_MODEL
        ) as rec:
            rec.set_prompt(serialize_prompt(system, messages))
            response = await self._client.chat.completions.create(
                model=_MODEL,
                max_tokens=512,
                messages=[{"role": "system", "content": system}, *messages],
            )
            raw = response.choices[0].message.content or ""
            tokens_in, tokens_out = _usage(response)
            rec.set_response(raw, tokens_in=tokens_in, tokens_out=tokens_out)
        return parse_ingredients(raw, text)
