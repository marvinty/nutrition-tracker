# MacroMic

A voice-first nutrition logging API. Speak what you ate, get macros back. Built with FastAPI, SQLite, OpenAI Whisper, and Anthropic Claude.

## Architecture

```
app/
├── core/        # Config (pydantic-settings, .env)
├── models/      # SQLAlchemy ORM models
├── schemas/     # Pydantic v2 request/response schemas
├── db/          # Async engine, session dependency, DB init
├── providers/   # Abstract LLMProvider + Claude implementation
├── services/    # Business logic (meals, audio transcription)
├── api/         # REST route handlers (meals, audio)
└── dashboard/   # Jinja2 web UI

client/
└── simulate.py  # macOS ESP32 simulator (mic → API → TTS)
```

**Dependency direction:** `api` → `services` → `providers` / `db` → `core`

### Key design decisions

- **Abstract `LLMProvider`** — swap or add providers by implementing one async method and setting `LLM_PROVIDER` in `.env`. See [Adding a new LLM provider](#adding-a-new-llm-provider).
- **`user_id: String` on every meal** — UUID-ready for future multi-tenancy; defaults to `"default"` for single-user mode.
- **SQLite in a named Docker volume** (`/data/macromic.db`) — persists across container rebuilds.
- **Whisper always via OpenAI** — speech-to-text is independent of the active `LLM_PROVIDER`.

## Quick Start (Docker)

```bash
# 1. Configure secrets
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and OPENAI_API_KEY

# 2. Start with hot-reload
make dev

# 3. Open the dashboard
open http://localhost:8000/dashboard

# 4. Browse the auto-generated API docs
open http://localhost:8000/docs
```

Other make targets:

```bash
make logs   # tail container logs
make stop   # bring down the stack
```

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/audio` | Upload audio → transcribe → extract macros → save meal |
| `POST` | `/meals` | Manually log a meal |
| `GET`  | `/meals` | List meals (`?user_id=&filter_date=YYYY-MM-DD`) |
| `GET`  | `/api/usage` | Today's AI credit budget (`used`, `limit`, `remaining`, `tier`, `system_available`) |
| `GET`  | `/dashboard` | Web UI showing today's meals and macro totals |

### POST /audio

```bash
curl -X POST http://localhost:8000/audio \
  -F "file=@recording.wav" \
  -F "user_id=alice"
```

Response:

```json
{
  "transcript": "I had two scrambled eggs and toast",
  "description": "2 scrambled eggs and 1 slice of toast",
  "calories": 320,
  "protein": 16.0,
  "carbs": 28.0,
  "fat": 14.0,
  "meal_id": 1
}
```

### POST /meals

```bash
curl -X POST http://localhost:8000/meals \
  -H "Content-Type: application/json" \
  -d '{"description": "Greek yogurt", "calories": 130, "protein": 17, "carbs": 8, "fat": 3}'
```

### GET /meals

```bash
curl "http://localhost:8000/meals?filter_date=2026-03-30"
```

## Deployment (Linux Server)

```bash
git clone <your-repo> && cd macromic
cp .env.example .env && nano .env   # set API keys

docker compose -f docker-compose.prod.yml up -d
```

The prod compose file:
- Omits the source volume mount (no hot-reload)
- Runs `uvicorn` with `--workers 2`
- Uses `restart: unless-stopped`

The `macromic_data` Docker volume persists the SQLite database.

## ESP32 Simulator (macOS)

The `client/simulate.py` script simulates an ESP32 device: it records 5 seconds of audio from your Mac microphone, sends it to the API, and reads the result aloud.

```bash
# One-time setup
brew install portaudio
pip install -r client/requirements.txt

# Run
python client/simulate.py

# Point at a different server
API_URL=http://192.168.1.10:8000 python client/simulate.py
```

## Adding a New LLM Provider

1. **Create the provider file** — e.g. `app/providers/openai.py`:

```python
from app.providers.base import LLMProvider, NutritionResult

class OpenAIProvider(LLMProvider):
    async def extract_nutrition(self, transcript: str) -> NutritionResult:
        # call OpenAI chat completions with a structured prompt
        ...
        return NutritionResult(description=..., calories=..., protein=..., carbs=..., fat=...)
```

2. **Register it** in `app/providers/__init__.py`:

```python
elif settings.llm_provider == "openai":
    from app.providers.openai import OpenAIProvider
    return OpenAIProvider()
```

3. **Activate it** in `.env`:

```
LLM_PROVIDER=openai
```

Restart the container — no other changes needed.

## Configuration

All settings are read from `.env` (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for Claude provider |
| `OPENAI_API_KEY` | — | Required for Whisper transcription (always) |
| `LLM_PROVIDER` | `claude` | Active LLM provider (`claude`, `openai`, `gemini`) |
| `DATABASE_URL` | `sqlite+aiosqlite:////data/macromic.db` | SQLAlchemy async DB URL |
| `APP_PORT` | `8000` | Host port exposed by Docker |
| `TIER_DAILY_CREDITS` | `{"free": 20, "pro": 300}` | Daily AI credit budget per user tier |
| `CREDIT_COSTS` | `{"text": 1, "clarify": 1, "voice": 3}` | Credits each action spends |
| `GLOBAL_DAILY_CREDITS` | `500` | App-wide daily ceiling across all users |
| `SIGNUP_CODE` | — | Invite code required to register; empty = open signup |

### Cost protection

Every endpoint that reaches an LLM or Whisper spends credits from a per-user daily
budget that resets at local midnight. Actions are weighted — a voice log costs more
than a text log because it pays for transcription *and* the analysis that follows.
Exceeding the budget returns `429` with a German message that the UI shows as-is.

The budget comes from the user's `tier` column (default `free`). There is no billing
yet, so promote by hand:

```bash
sqlite3 /data/macromic.db "UPDATE user SET tier='pro' WHERE username='marvin'"
```

Two further layers sit on top, because per-user limits alone cannot stop a burst of
new signups or a client stuck in a retry loop:

- **`GLOBAL_DAILY_CREDITS`** is an app-wide ceiling tracked under a `__global__` row in
  the same table. Keep it well above normal usage — it is a circuit breaker, not a
  rationing tool. When it trips, *every* user is locked out until local midnight; that
  is the deliberate trade against a surprise bill. The 429 message is worded differently
  from the per-user one so the two cases are distinguishable in the logs.
- **`SIGNUP_CODE`** closes registration. Without it, anyone can create accounts and spend
  free credits, and the ceiling only limits how bad that gets. Leave it unset only for
  local dev — the app logs a warning on every boot while signup is open.

Neither protects you from a bug in this app's own limiting code. Set a spend limit in the
Anthropic Console as the backstop that does not depend on it.
