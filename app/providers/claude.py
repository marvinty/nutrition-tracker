from anthropic import AsyncAnthropic
from app.providers.base import (
    AnalysisResult,
    LLMProvider,
    build_system_prompt,
    parse_analysis,
)
from app.core.config import settings


class ClaudeProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def analyze(
        self, messages: list[dict], allow_questions: bool
    ) -> AnalysisResult:
        message = await self._client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=256,
            system=build_system_prompt(allow_questions),
            messages=messages,
        )
        raw = message.content[0].text
        return parse_analysis(raw, messages, allow_questions)
