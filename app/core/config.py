from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    openai_api_key: str = ""
    llm_provider: Literal["claude", "openai", "gemini"] = "claude"
    whisper_provider: Literal["local", "openai"] = "local"
    whisper_model: str = "base"  # local only: tiny | base | small | medium | large
    database_url: str = "sqlite+aiosqlite:////data/nutrition.db"
    app_port: int = 8000

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
