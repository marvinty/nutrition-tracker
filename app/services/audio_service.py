from io import BytesIO
from openai import AsyncOpenAI
from app.core.config import settings

_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """Send audio bytes to OpenAI Whisper API and return transcript text."""
    audio_file = BytesIO(audio_bytes)
    audio_file.name = filename  # Extension is used by the SDK to set Content-Type
    transcript = await _client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
    )
    return transcript.text
