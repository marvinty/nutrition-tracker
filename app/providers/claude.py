from anthropic import AsyncAnthropic
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

# Lifted out of the call so the log records exactly the string that was sent,
# rather than a second copy that could drift from it.
_MODEL = "claude-3-5-haiku-20241022"


class ClaudeProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def analyze(
        self, messages: list[dict], allow_questions: bool
    ) -> AnalysisResult:
        system = build_system_prompt(allow_questions)
        async with log_ai_call(
            kind="llm_analyze", provider="claude", model=_MODEL
        ) as rec:
            rec.set_prompt(serialize_prompt(system, messages))
            message = await self._client.messages.create(
                model=_MODEL,
                max_tokens=256,
                system=system,
                messages=messages,
            )
            raw = message.content[0].text
            rec.set_response(
                raw,
                tokens_in=message.usage.input_tokens,
                tokens_out=message.usage.output_tokens,
            )
        # Outside the block: a parse failure is the app's bug, not the call's, and
        # the row should say the call succeeded — with the raw text that broke it.
        return parse_analysis(raw, messages, allow_questions)

    async def extract_ingredients(self, text: str) -> list[NutritionResult]:
        system = build_ingredients_prompt()
        messages = [{"role": "user", "content": text}]
        async with log_ai_call(
            kind="llm_ingredients", provider="claude", model=_MODEL
        ) as rec:
            rec.set_prompt(serialize_prompt(system, messages))
            message = await self._client.messages.create(
                model=_MODEL,
                max_tokens=512,
                system=system,
                messages=messages,
            )
            raw = message.content[0].text
            rec.set_response(
                raw,
                tokens_in=message.usage.input_tokens,
                tokens_out=message.usage.output_tokens,
            )
        return parse_ingredients(raw, text)
