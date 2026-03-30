from abc import ABC, abstractmethod


class WhisperProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        """Transcribe audio bytes and return the transcript text."""
        ...
