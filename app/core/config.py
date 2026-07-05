from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    openai_api_key: str = ""
    llm_provider: Literal["claude", "openai", "gemini"] = "claude"
    whisper_provider: Literal["local", "openai"] = "local"
    whisper_model: str = "base"  # local only: tiny | base | small | medium | large
    database_url: str = "sqlite+aiosqlite:////data/nutrition.db"
    app_timezone: str = "Europe/Berlin"  # local tz for day boundaries and display
    app_port: int = 8000
    session_cookie_name: str = "session"
    session_ttl_days: int = 30
    cookie_secure: bool = False  # set True in production (HTTPS)

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
