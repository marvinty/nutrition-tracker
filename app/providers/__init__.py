from app.core.config import settings
from app.providers.base import LLMProvider


def get_provider() -> LLMProvider:
    if settings.llm_provider == "claude":
        from app.providers.claude import ClaudeProvider
        return ClaudeProvider()
    elif settings.llm_provider == "openai":
        from app.providers.openai import OpenAIProvider  # type: ignore[import]
        return OpenAIProvider()
    elif settings.llm_provider == "gemini":
        from app.providers.gemini import GeminiProvider  # type: ignore[import]
        return GeminiProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider!r}")
