from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    openai_api_key: str = ""
    llm_provider: Literal["claude", "openai", "gemini"] = "claude"
    whisper_provider: Literal["local", "openai"] = "local"
    whisper_model: str = "base"  # local only: tiny | base | small | medium | large
    # Cost protection: each AI call spends credits from a daily per-user budget that
    # depends on the user's tier. An unknown tier falls back to "free", so a typo in
    # the DB can never hand out an unlimited budget.
    tier_daily_credits: dict[str, int] = {"free": 20, "pro": 300}
    # Voice costs more because it pays for transcription *and* the LLM analysis.
    credit_costs: dict[str, int] = {"text": 1, "clarify": 1, "voice": 3}
    # App-wide ceiling across all users. A circuit breaker, not a rationing tool:
    # keep it well above the expected daily sum so it only trips when something is
    # wrong (a signup burst, a client stuck in a retry loop). Tripping it locks out
    # every user until local midnight — the deliberate trade against a surprise bill.
    global_daily_credits: int = 500
    # Invite code required to register. Empty means registration is open, which the
    # app warns about at startup.
    signup_code: str = ""
    # Transactional email (verification, password reset) via Resend's HTTP API.
    # Leaving the key empty makes send_email log the message instead of sending it, so
    # local development and tests exercise the real flows without network or a mock.
    resend_api_key: str = ""
    email_from: str = "Nutrition Tracker <noreply@example.com>"
    # How long a new account may go unconfirmed before it is locked. The lock is
    # reversible from the block page itself, so this can be short.
    email_verify_grace_minutes: int = 60
    # Absolute origin for links in outgoing mail. request.base_url reports the internal
    # address behind a reverse proxy, which would produce unreachable links.
    public_base_url: str = "http://localhost:8000"
    database_url: str = "sqlite+aiosqlite:////data/nutrition.db"
    app_timezone: str = "Europe/Berlin"  # local tz for day boundaries and display
    app_port: int = 8000
    session_cookie_name: str = "session"
    session_ttl_days: int = 30
    cookie_secure: bool = False  # set True in production (HTTPS)

    # Admin panel (/admin). Separate credentials, table and cookie from app users.
    # Setting both env vars creates the admin on startup, or resets its password
    # if it already exists — the recovery path for a deployment with no shell.
    admin_username: str = ""
    admin_password: str = ""
    admin_session_cookie_name: str = "admin_session"
    admin_session_ttl_days: int = 7  # shorter-lived than a user session

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
