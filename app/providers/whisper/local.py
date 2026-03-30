import asyncio
import os
import tempfile
from typing import Optional

from app.providers.whisper.base import WhisperProvider


class LocalWhisperProvider(WhisperProvider):
    """
    Runs OpenAI Whisper locally via the `openai-whisper` package.
    The model is loaded lazily on first use and cached for subsequent calls.

    Available models (speed vs. accuracy trade-off):
        tiny, base, small, medium, large
    Set WHISPER_MODEL in .env to choose. Defaults to "base".
    """

    def __init__(self, model_name: str = "base") -> None:
        self._model_name = model_name
        self._model: Optional[object] = None

    def _get_model(self):
        if self._model is None:
            import whisper  # openai-whisper package
            self._model = whisper.load_model(self._model_name)
        return self._model

    async def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        suffix = os.path.splitext(filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            model = self._get_model()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: model.transcribe(tmp_path))
            return result["text"].strip()
        finally:
            os.unlink(tmp_path)
