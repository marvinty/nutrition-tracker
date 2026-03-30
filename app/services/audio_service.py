from app.providers.whisper import get_whisper_provider


async def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """Transcribe audio using the configured whisper provider."""
    provider = get_whisper_provider()
    return await provider.transcribe(audio_bytes, filename)
