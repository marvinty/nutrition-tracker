"""Full-text logging of every outgoing AI call.

The awkward part of this feature is that the two halves of a log row live in
different places. The provider knows the model name, the token usage and the raw
response — none of which it returns, since ``analyze`` hands back a parsed
``NutritionResult`` and drops ``raw`` on the floor. The endpoint knows who is
calling and which action paid for it. Neither can see the other's half.

Rather than thread a context object through ``analyze`` / ``extract_ingredients``
/ ``transcribe`` / ``run_analysis`` / ``transcribe_audio`` and every call site —
six signatures, and every fake provider in the test suite broken — the caller's
half travels in a ``ContextVar`` set once in ``require_credits``, and the
provider's half is captured by ``log_ai_call`` wrapped around the API call.
Uvicorn runs each request in its own asyncio task, so the ContextVar is
task-local and cannot leak between concurrent requests.
"""

import json
import logging
import re
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.ai_request_log import AiRequestLog

logger = logging.getLogger(__name__)

_TRUNCATION_MARKER = " …[gekürzt]"
# An exception's str() can be arbitrarily long (a provider echoing back the whole
# request body, say), and it lands in a String column read in a table cell.
_MAX_ERROR_CHARS = 500


@dataclass
class AiCallContext:
    """The half of a log row only the request knows."""

    username: Optional[str]
    action: Optional[str]
    endpoint: Optional[str]


_context: ContextVar[Optional[AiCallContext]] = ContextVar("ai_call_context", default=None)


def set_ai_context(
    username: Optional[str], action: Optional[str], endpoint: Optional[str]
) -> None:
    _context.set(AiCallContext(username=username, action=action, endpoint=endpoint))


def current_ai_context() -> Optional[AiCallContext]:
    return _context.get()


def _truncate(text: Optional[str], limit: Optional[int] = None) -> Optional[str]:
    if text is None:
        return None
    cap = settings.ai_log_max_text_chars if limit is None else limit
    if len(text) <= cap:
        return text
    return text[:cap] + _TRUNCATION_MARKER


def serialize_prompt(system: str, messages: list[dict]) -> str:
    """Render what was actually sent to an LLM as one readable blob.

    Includes the system prompt because that is where the app's own behaviour
    lives: a log without it cannot explain why the model answered as it did.
    """
    return json.dumps(
        {"system": system, "messages": messages}, ensure_ascii=False, indent=2
    )


class AiCallRecorder:
    """Handed to the body of ``log_ai_call`` to collect the provider's half."""

    def __init__(self) -> None:
        self.request_text: str = ""
        self.response_text: Optional[str] = None
        self.prompt_tokens: Optional[int] = None
        self.completion_tokens: Optional[int] = None

    def set_prompt(self, text: str) -> None:
        self.request_text = text

    def set_response(
        self,
        text: Optional[str],
        *,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
    ) -> None:
        self.response_text = text
        self.prompt_tokens = tokens_in
        self.completion_tokens = tokens_out


async def _write(**fields) -> None:
    """Persist one row on its own session, swallowing anything that goes wrong.

    Its own session, not the request-scoped one, for two reasons that both come
    down to the log having to outlive the work it describes: ``consume_credits``
    rolls the request session back on a 429, and a failed AI call raises
    HTTPException, so the request session closes without ever committing. Writing
    here and committing immediately keeps the row regardless.

    Swallowing errors is deliberate. Logging is observability, never a reason for
    a working AI call to fail — so a broken write costs a log line, not a request.
    """
    try:
        async with async_session_maker() as session:
            session.add(AiRequestLog(**fields))
            await session.commit()
    except Exception:  # noqa: BLE001 — see docstring: must never reach the caller
        logger.exception("KI-Anfrage konnte nicht protokolliert werden")


@asynccontextmanager
async def log_ai_call(
    *, kind: str, provider: str, model: Optional[str] = None
) -> AsyncIterator[AiCallRecorder]:
    """Time an AI call and record it, whether it succeeds or raises.

    Usage inside a provider method::

        async with log_ai_call(kind="llm_analyze", provider="claude", model=_MODEL) as rec:
            rec.set_prompt(serialize_prompt(system, messages))
            message = await client.messages.create(...)
            rec.set_response(raw, tokens_in=..., tokens_out=...)

    The failure row is written before the exception is re-raised, so a provider
    outage leaves a trace even though the request ends as a 502.
    """
    recorder = AiCallRecorder()
    ctx = current_ai_context()
    started = time.perf_counter()

    async def record(*, success: bool, error: Optional[str]) -> None:
        await _write(
            user_id=ctx.username if ctx else None,
            action=ctx.action if ctx else None,
            endpoint=ctx.endpoint if ctx else None,
            kind=kind,
            provider=provider,
            model=model,
            request_text=_truncate(recorder.request_text) or "",
            response_text=_truncate(recorder.response_text),
            prompt_tokens=recorder.prompt_tokens,
            completion_tokens=recorder.completion_tokens,
            latency_ms=int((time.perf_counter() - started) * 1000),
            success=success,
            error=error,
        )

    try:
        yield recorder
    # Exception, not BaseException: a cancelled request (client disconnect) would
    # otherwise try to await a database write while the task is being torn down,
    # and the CancelledError raised by that write would replace the original.
    # Losing the log line for an abandoned request is the better trade.
    except Exception as exc:
        await record(
            success=False,
            error=_truncate(f"{type(exc).__name__}: {exc}", _MAX_ERROR_CHARS),
        )
        raise
    await record(success=True, error=None)


async def list_logs_for_user(
    session: AsyncSession, username: str, limit: int = 100
) -> list[AiRequestLog]:
    """Newest calls first. Scoped by username, so the later user-facing view can
    reuse this unchanged by passing the caller's own name."""
    result = await session.execute(
        select(AiRequestLog)
        .where(AiRequestLog.user_id == username)
        .order_by(AiRequestLog.created_at.desc(), AiRequestLog.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


@dataclass
class UserLogEntry:
    """One AI call as its own user may see it.

    Not the raw row: ``request_text`` holds the system prompt and the conversation
    as JSON, which is both unreadable and internal. This carries only the two
    things the user contributed or received — what they said, and what came back.
    """

    created_at: datetime
    kind: str
    action: Optional[str]
    input_text: str
    output_text: Optional[str]
    success: bool


def _strip_fences(raw: str) -> str:
    """Mirror of the cleaning in ``providers.base`` — models like to wrap JSON."""
    return re.sub(r"```json?\s*|\s*```", "", raw or "").strip()


def _input_from_row(log: AiRequestLog) -> str:
    """The user's own words, dug out of the serialized prompt."""
    if log.kind == "transcribe":
        # The audio placeholder says nothing; the transcript below is the input.
        return "🎤 Sprachaufnahme"
    try:
        payload = json.loads(log.request_text)
        for message in reversed(payload.get("messages", [])):
            if message.get("role") == "user":
                return message.get("content", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass
    return ""


def _output_from_row(log: AiRequestLog) -> Optional[str]:
    """The readable result: a transcript, a description, or a clarifying question."""
    if not log.success:
        return None
    if log.kind == "transcribe":
        return log.response_text
    try:
        data = json.loads(_strip_fences(log.response_text or ""))
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(data, list):  # ingredient extraction returns an array
        parts = [i.get("description") for i in data if isinstance(i, dict)]
        return ", ".join(p for p in parts if p) or None
    if isinstance(data, dict):
        return data.get("question") or data.get("description")
    return None


async def list_user_entries(
    session: AsyncSession, username: str, limit: int = 50
) -> list[UserLogEntry]:
    """The user-facing view of their own AI calls."""
    return [
        UserLogEntry(
            created_at=log.created_at,
            kind=log.kind,
            action=log.action,
            input_text=_input_from_row(log),
            output_text=_output_from_row(log),
            success=log.success,
        )
        for log in await list_logs_for_user(session, username, limit=limit)
    ]


async def prune_old_logs(
    session: AsyncSession, retention_days: Optional[int] = None
) -> int:
    """Drop rows past the retention window. Called at boot, mirroring
    ``rate_limit_service.prune_expired`` — no scheduler needed, and the window is
    the promise that justifies storing verbatim user input in the first place."""
    days = settings.ai_log_retention_days if retention_days is None else retention_days
    # Naive UTC: SQLite hands back naive datetimes, and mixing an aware value into
    # a WHERE clause raises as soon as SQLAlchemy evaluates it. Same reasoning as
    # rate_limit_service._utcnow.
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    result = await session.execute(
        delete(AiRequestLog)
        .where(AiRequestLog.created_at <= cutoff)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return result.rowcount
