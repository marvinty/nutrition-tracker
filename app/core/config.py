from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    openai_api_key: str = ""
    llm_provider: Literal["claude", "openai", "gemini"] = "claude"
    database_url: str = "sqlite+aiosqlite:////data/nutrition.db"
    app_port: int = 8000

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
