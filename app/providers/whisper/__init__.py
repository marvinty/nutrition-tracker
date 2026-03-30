from app.core.config import settings
from app.providers.whisper.base import WhisperProvider

_provider: WhisperProvider | None = None


def get_whisper_provider() -> WhisperProvider:
    global _provider
    if _provider is None:
        if settings.whisper_provider == "local":
            from app.providers.whisper.local import LocalWhisperProvider
            _provider = LocalWhisperProvider(model_name=settings.whisper_model)
        elif settings.whisper_provider == "openai":
            from app.providers.whisper.openai_provider import OpenAIWhisperProvider
            _provider = OpenAIWhisperProvider()
        else:
            raise ValueError(f"Unknown whisper provider: {settings.whisper_provider!r}")
    return _provider
