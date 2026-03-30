from io import BytesIO

from openai import AsyncOpenAI

from app.core.config import settings
from app.providers.whisper.base import WhisperProvider


class OpenAIWhisperProvider(WhisperProvider):
    """Transcribes audio via the OpenAI Whisper API (whisper-1)."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        audio_file = BytesIO(audio_bytes)
        audio_file.name = filename  # SDK uses the extension to set Content-Type
        transcript = await self._client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        return transcript.text
