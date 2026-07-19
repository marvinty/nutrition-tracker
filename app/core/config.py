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
    # Full-text log of every AI call (see models/ai_request_log.py). The retention
    # window is what keeps storing verbatim user input defensible, and the char cap
    # stops one pathological request from bloating the SQLite file.
    ai_log_retention_days: int = 90
    ai_log_max_text_chars: int = 20000
    # Invite code required to register. Empty means registration is open, which the
    # app warns about at startup.
    signup_code: str = ""
    # Transactional email (verification, password reset) via Resend's HTTP API.
    # Leaving the key empty makes send_email log the message instead of sending it, so
    # local development and tests exercise the real flows without network or a mock.
    resend_api_key: str = ""
    email_from: str = "MacroMic <noreply@example.com>"
    # How long a new account may go unconfirmed before it is locked. The lock is
    # reversible from the block page itself, so this can be short.
    email_verify_grace_minutes: int = 60
    # Absolute origin for links in outgoing mail. request.base_url reports the internal
    # address behind a reverse proxy, which would produce unreachable links.
    public_base_url: str = "http://localhost:8000"
    database_url: str = "sqlite+aiosqlite:////data/macromic.db"
    app_timezone: str = "Europe/Berlin"  # local tz for day boundaries and display
    app_port: int = 8000
    session_cookie_name: str = "session"
    session_ttl_days: int = 30
    cookie_secure: bool = False  # set True in production (HTTPS)

    # How many reverse proxies of ours sit in front of the app. Decides which entry of
    # X-Forwarded-For is trustworthy — see core/client_ip.py. Default 0 (no proxy) is
    # the safe one: it ignores the header entirely rather than trusting a value any
    # client can set. Set to 1 when running behind Caddy/nginx/Traefik.
    trusted_proxy_hops: int = 0
    # Failed sign-in attempts allowed per window, counted per IP and per account. Only
    # failures count, so normal use never runs into it.
    login_rate_limit: int = 10
    login_rate_window_minutes: int = 15
    # Mails are the expensive, abusable side of these two, so they get their own budget.
    signup_rate_limit: int = 5
    forgot_password_rate_limit: int = 5

    # Admin panel (/admin). Separate credentials, table and cookie from app users.
    # Setting both env vars creates the admin on startup, or resets its password
    # if it already exists — the recovery path for a deployment with no shell.
    admin_username: str = ""
    admin_password: str = ""
    admin_session_cookie_name: str = "admin_session"
    admin_session_ttl_days: int = 7  # shorter-lived than a user session

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
