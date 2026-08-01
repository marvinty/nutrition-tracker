# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MacroMic — a voice-first nutrition log. The user says what they ate, Whisper transcribes it,
an LLM estimates macros, the meal is saved. FastAPI + async SQLAlchemy + SQLite, with a
server-rendered Jinja2 UI. Deployed as Docker Compose on a home Proxmox box behind Caddy.

## Commands

```bash
make dev      # docker compose up --build (hot reload, http://localhost:8000)
make logs     # tail container logs
make stop     # docker compose down
```

Tests run on the host, not in the container — pytest is the only thing that works against the
local Python:

```bash
python3 -m pytest -q --ignore=tests/test_rate_limit_page.py --ignore=tests/test_register_form.py
python3 -m pytest tests/test_goals.py -q            # one file
python3 -m pytest tests/test_goals.py -k upsert -q  # one test
```

The two ignored modules go over httpx/ASGITransport. `httpx` is a project dependency but is
not installed in the local Python 3.9, so without the flags the run dies at collection. They
pass in the container, which has httpx but not pytest — so the full suite needs a one-off
install (196 tests locally, 202 there):

```bash
docker exec nutrition-tracker-api-1 pip install -q pytest pytest-asyncio
docker exec -w /app nutrition-tracker-api-1 python -m pytest -q
```

The local interpreter is Python 3.9 while the app targets 3.12 in Docker. Anything beyond
pytest (starting uvicorn, importing the full app) must go through `make dev` — `from app.main
import app` fails locally on PEP 604 syntax.

Production deploy runs on the Proxmox host:

```bash
docker compose -f docker-compose.prod.yml up -d
```

Changes to `.env` need `up -d`, not `restart` — Compose only re-reads the env file when the
container is recreated. Settings are read at import time, so any `.env` change needs a
restart of the process regardless.

## Architecture

Dependency direction is `api`/`dashboard`/`auth`/`admin` → `services` → `providers`/`db` → `core`.
Routers hold no business logic; services own it and take an `AsyncSession` as their first
argument. Tests exercise services directly (see below), which is what keeps that boundary real.

**Five routers**, all registered in `app/main.py`:

| Router | Prefixes | Renders |
|---|---|---|
| `landing` | `/`, `/faq` | public HTML |
| `auth` | `/login`, `/register`, `/verify-email/*`, `/reset-password`, … | HTML forms |
| `api` | `/meals`, `/audio`, `/api/recipes`, `/api/goals`, `/api/usage` | JSON |
| `dashboard` | `/dashboard`, `/history`, `/goals`, `/recipes`, `/ai-log`, `/feedback` | HTML |
| `admin` | `/admin/*` | HTML, separate credentials |

`/meals` and `/audio` sit at the root without an `/api` prefix — legacy paths for the ESP32
client. Several places (the 429 handler, the CSRF rejection, `EmailVerificationRequired`)
branch on `/api/` as the "is this a machine caller" test, so those two endpoints are
deliberately handled by `Accept: text/html` instead of by path. Don't unify these.

**LLM providers** are swappable behind `app/providers/base.LLMProvider`; `get_provider()`
dispatches on `settings.llm_provider` with the import inside the branch, so an uninstalled
provider's SDK never breaks startup. `analyze()` returns either a `NutritionResult` or a
`ClarificationNeeded`, and `services/nutrition_flow.run_analysis` turns that into one turn of
the conversation — at most `MAX_QUESTIONS` (2) assistant turns before the model is forced to
estimate.

**Whisper is independent of `LLM_PROVIDER`.** `WHISPER_PROVIDER=openai` is the only value that
works: `torch`/`openai-whisper` were removed from `requirements.txt` and the Dockerfile to shrink
the image. `LocalWhisperProvider` imports `whisper` lazily on first transcription, so
`get_whisper_provider()` checks for the package up front and raises a RuntimeError explaining the
fix — otherwise a misconfigured deployment looks healthy until someone records a meal.
`OPENAI_API_KEY` is therefore always required, whatever `LLM_PROVIDER` is set to.

### Cross-cutting mechanisms

These are the pieces that are easy to break without reading them first.

**Credits** (`core/deps.require_credits`, `services/usage_service`). Every endpoint that reaches
an LLM or Whisper depends on `require_credits("<action>")`, which charges before doing the work
and raises 429 when either the user's tier budget or the app-wide `GLOBAL_DAILY_CREDITS` ceiling
is exhausted. Both reset at local midnight. `clarify` costs the user 0 (the model asked the
question) but still costs 1 against the global ceiling, because a caller posting fresh
one-message conversations would otherwise be unmetered. **New AI endpoint ⇒ add the dependency.**

**AI logging** (`services/ai_log_service`). Every AI call is logged in full. The row's two halves
come from different places — the caller's half (username, action, endpoint) is put into a
`ContextVar` by `require_credits`, the provider's half (model, tokens, raw response) is captured
by the `log_ai_call` context manager around the API call. That's why neither signature carries a
context object. It works because uvicorn runs each request in its own asyncio task.

**CSRF** (`core/csrf`). Double-submit cookie, written as raw ASGI rather than `BaseHTTPMiddleware`
because reading the form body in middleware would otherwise consume the stream before the handler
sees it. Forms use `{{ csrf_field() }}` (a Jinja global, registered per template environment via
`register_csrf_field` — a new template dir must call it); fetch calls send `X-CSRF-Token`;
`Authorization: Bearer` requests are exempt.

**Sessions and email lock** (`core/deps.resolve_user`). Cookie first, then bearer token. An
account whose email is still unconfirmed past `EMAIL_VERIFY_GRACE_MINUTES` raises
`EmailVerificationRequired` from the dependency, which `main.py` turns into a redirect (browser)
or 403 (API). `_LOCK_EXEMPT_PATHS` is what keeps the lock from being a dead end.
`request.state.verify_banner` is set to a plain string, not the `User`, because an error page can
render after the session was rolled back and touching an ORM attribute then raises
`DetachedInstanceError`.

**Time** (`core/time`). Timestamps are stored tz-aware UTC; "which day" and all display use
`settings.app_timezone` (Europe/Berlin). Use `today_local()` / `day_bounds()` / `to_local()`
rather than `datetime.now()` — day boundaries and DST correctness depend on it.

### Database

SQLite, single uvicorn worker on purpose (two processes contend for the write lock; see the
comment in `docker-compose.prod.yml`). `db/session.py` sets `journal_mode=WAL` and
`busy_timeout=5000` on every connection, guarded on the dialect because the move off SQLite is
explicitly provisional.

**There is no Alembic.** `db/init_db.py` runs `create_all` plus hand-written migration functions
at startup. `create_all` creates missing *tables* only, never missing *columns*, so every column
added to an existing table needs its own function there. The established pattern:

- guard on `PRAGMA table_info(...)` and return early if the column exists (idempotent across restarts)
- `ALTER TABLE ... ADD COLUMN` can't be UNIQUE — add a separate `CREATE UNIQUE INDEX IF NOT EXISTS`
- backfill in its own `UPDATE`, and think about what the new column means for rows that already
  exist (the email migration had to grandfather existing users in as verified, or every live user
  would have been locked out on deploy)
- new models must be imported in `init_db.py` to register with `Base.metadata`

Retention pruning (`prune_expired`, `prune_old_logs`) runs at boot rather than on a scheduler.

## Tests

No `conftest.py`, no `TestClient`. Each test file is self-contained and follows the same shape:

```python
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")   # config requires it at import time
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
```

…set *before* importing any `app` module, then a `pytest_asyncio` fixture builds an in-memory
engine and `Base.metadata.create_all`. Tests call services directly. HTTP-level behaviour
(cookies, redirects, form parsing) is verified by hand against a running container, not in pytest.
`asyncio_mode = strict`, so every async test needs `@pytest.mark.asyncio`.

Leaving `RESEND_API_KEY` empty makes `send_email` log the message instead of sending it, so the
real mail flows are exercised in tests and local dev without a mock.

## UI conventions

[DESIGN.md](DESIGN.md) is binding for anything user-facing, and says so: "nichts dazuerfinden".
The rules that get violated most often:

- **Everything is German** — UI copy, error messages, `detail` strings on `HTTPException`. Several
  of these strings are rendered to the user as-is.
- Only the color tokens in DESIGN.md. No new base colors, no emojis, no dark mode.
- Fonts: Newsreader (headings, numbers), Inter (body). Du-Ansprache, no marketing voice.
- Responsive down to 375px, no horizontal scroll. CSS-only animation, always respecting
  `prefers-reduced-motion`.
- CSS is inlined per template; `/static` holds brand assets only ([BRAND.md](BRAND.md)).

## Tooling in `.claude/`

All of this is checked in and applies to every checkout. `.claude/settings.local.json` is the
one exception — gitignored, per-machine.

### Hooks that run on their own

**`.env` is blocked** (`hooks/block-env-access.sh`, PreToolUse on Read/Edit/Write/Bash/Grep,
plus `permissions.deny`). `.env` and `.env.*` hold live production credentials; reading one
copies a secret into the transcript permanently, where no later cleanup reaches it.
`.env.example` is allowed and documents every key.

The guard matches on the command text, so it cannot tell reading the file from naming it — a
commit message or a grep pattern that merely contains `.env` is refused too. Work around it
with `git commit -F <file>` rather than weakening the hook. If a real value is needed, ask
Marvin; do not try to route around the block.

**Tests run after edits under `app/`** (`hooks/run-tests-on-app-edit.sh`, PostToolUse on
Write/Edit, async). Green is silent; a failure wakes the model with the failing test named. It
covers the 196 local tests, not the six httpx ones. It is not a substitute for running the
suite yourself before saying something works.

### Skills — invoke these, don't improvise

- **`/add-column`** — before adding any column to an existing table. There is no Alembic and
  `create_all` will not add it; the skill carries the idempotency guard, the UNIQUE-via-index
  rule and the backfill question.
- **`/deploy`** — before deploying to the Proxmox host. Includes the three restart rules and
  the prod env vars to re-check.

Both are user-invocable only (`disable-model-invocation: true`), so suggest them rather than
expecting them to fire on their own.

### Subagents — suggest them at the right moment

Neither runs automatically, and this harness does not spawn agents unbidden. Recommend them:

- **`design-system-reviewer`** — after touching any template or user-facing string.
- **`sqlite-migration-reviewer`** — after any change to `init_db.py` or `app/models/`.

### MCP servers

`.mcp.json` declares **context7** (live SQLAlchemy 2.0 async / FastAPI docs — recall skews to
the older sync idioms) and the **GitHub** server. Both need approval on first connect; GitHub
also needs an OAuth sign-in. If they are not connected, they are simply absent — do not stall
waiting for them.

### Permissions

`.claude/settings.json` allows a small read-only set (pytest, `docker compose logs`/`ps`,
`docker info`, `dig`, the page-reading browser tools). Deliberately absent: `curl`, because a
prefix wildcard cannot be pinned to GET; and interpreters, package runners and
`docker compose exec`, because they are arbitrary code execution. Expect prompts for those.

## Note on the README

[README.md](README.md) predates the auth, admin, credit and email work and has drifted — it
describes `--workers 2` (prod now runs one worker deliberately), Whisper via a provider that no
longer ships, and an API surface without authentication. Treat the code as authoritative and
DESIGN.md/BRAND.md as current.
