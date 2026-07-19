from io import BytesIO

from openai import AsyncOpenAI

from app.core.config import settings
from app.providers.whisper.base import WhisperProvider
from app.services.ai_log_service import log_ai_call

_MODEL = "whisper-1"


class OpenAIWhisperProvider(WhisperProvider):
    """Transcribes audio via the OpenAI Whisper API (whisper-1)."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        async with log_ai_call(
            kind="transcribe", provider="openai", model=_MODEL
        ) as rec:
            # The audio itself is not stored — only enough to correlate a log entry
            # with what the user sent. The transcript below is the readable half.
            rec.set_prompt(f"<audio {len(audio_bytes)} bytes, {filename}>")
            audio_file = BytesIO(audio_bytes)
            audio_file.name = filename  # SDK uses the extension to set Content-Type
            transcript = await self._client.audio.transcriptions.create(
                model=_MODEL,
                file=audio_file,
            )
            rec.set_response(transcript.text)  # no token counts on this endpoint
        return transcript.text
