import importlib.util

from app.core.config import settings
from app.providers.whisper.base import WhisperProvider

_provider: WhisperProvider | None = None


def get_whisper_provider() -> WhisperProvider:
    global _provider
    if _provider is None:
        if settings.whisper_provider == "local":
            # LocalWhisperProvider imports `whisper` lazily, on first transcription
            # rather than here, so without this check a misconfigured deployment would
            # look healthy until someone recorded a meal and then fail with a bare
            # ModuleNotFoundError. find_spec answers the question without paying for
            # the (slow) torch import on the path where the package *is* present.
            if importlib.util.find_spec("whisper") is None:
                raise RuntimeError(
                    "WHISPER_PROVIDER=local needs the openai-whisper and torch packages, "
                    "which were removed from requirements.txt and the Dockerfile to keep "
                    "the image small. Set WHISPER_PROVIDER=openai, or add them back."
                )
            from app.providers.whisper.local import LocalWhisperProvider
            _provider = LocalWhisperProvider(model_name=settings.whisper_model)
        elif settings.whisper_provider == "openai":
            from app.providers.whisper.openai_provider import OpenAIWhisperProvider
            _provider = OpenAIWhisperProvider()
        else:
            raise ValueError(f"Unknown whisper provider: {settings.whisper_provider!r}")
    return _provider
