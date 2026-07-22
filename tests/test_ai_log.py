"""Tests for the AI request log: the context manager that records a call, the
request context it reads, and the retention prune.

Like the other test modules these exercise the service layer directly against an
in-memory SQLite database. Config requires an API key at import time, so dummy
env vars are set before importing app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.ai_request_log import AiRequestLog
from app.models.base import Base
from app.services import ai_log_service
from app.services.ai_log_service import (
    get_token_totals,
    list_logs_for_user,
    list_user_entries,
    log_ai_call,
    prune_old_logs,
    serialize_prompt,
    set_ai_context,
    token_totals_by_user,
)


@pytest_asyncio.fixture
async def session(monkeypatch):
    """A session plus the maker ``log_ai_call`` writes through.

    ``_write`` deliberately opens its own session so a log row survives a rolled
    back request, which means the test database has to be substituted at the
    module level rather than passed in.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(ai_log_service, "async_session_maker", maker)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest.fixture(autouse=True)
def clear_context():
    """Each test starts without a request context — ContextVars outlive a test."""
    set_ai_context(None, None, None)


async def _rows(session) -> list[AiRequestLog]:
    result = await session.execute(select(AiRequestLog).order_by(AiRequestLog.id))
    return list(result.scalars().all())


# --- recording ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_call_is_recorded(session):
    async with log_ai_call(kind="llm_analyze", provider="claude", model="haiku") as rec:
        rec.set_prompt("Was habe ich gegessen?")
        rec.set_response("200 kcal", tokens_in=12, tokens_out=5)

    row = (await _rows(session))[0]
    assert row.kind == "llm_analyze"
    assert row.provider == "claude"
    assert row.model == "haiku"
    assert row.request_text == "Was habe ich gegessen?"
    assert row.response_text == "200 kcal"
    assert row.prompt_tokens == 12
    assert row.completion_tokens == 5
    assert row.success is True
    assert row.error is None
    assert row.latency_ms >= 0


@pytest.mark.asyncio
async def test_failed_call_is_recorded_and_still_raises(session):
    """A provider outage must leave a trace even though the request ends as a 502."""
    with pytest.raises(RuntimeError):
        async with log_ai_call(kind="transcribe", provider="openai") as rec:
            rec.set_prompt("<audio 42 bytes, meal.webm>")
            raise RuntimeError("upstream ist weg")

    row = (await _rows(session))[0]
    assert row.success is False
    assert "RuntimeError" in row.error
    assert "upstream ist weg" in row.error
    assert row.request_text == "<audio 42 bytes, meal.webm>"
    assert row.response_text is None


@pytest.mark.asyncio
async def test_context_is_attached_to_the_row(session):
    set_ai_context("alice", "voice", "/api/audio")
    async with log_ai_call(kind="transcribe", provider="local", model="base") as rec:
        rec.set_prompt("<audio>")
        rec.set_response("Zwei Eier")

    row = (await _rows(session))[0]
    assert row.user_id == "alice"
    assert row.action == "voice"
    assert row.endpoint == "/api/audio"


@pytest.mark.asyncio
async def test_call_without_context_is_still_recorded(session):
    """A call made outside a request should lose its attribution, not the row."""
    async with log_ai_call(kind="llm_analyze", provider="claude") as rec:
        rec.set_prompt("x")
        rec.set_response("y")

    row = (await _rows(session))[0]
    assert row.user_id is None
    assert row.action is None
    assert row.endpoint is None


@pytest.mark.asyncio
async def test_long_texts_are_truncated(session, monkeypatch):
    monkeypatch.setattr(settings, "ai_log_max_text_chars", 50)
    async with log_ai_call(kind="llm_analyze", provider="claude") as rec:
        rec.set_prompt("a" * 500)
        rec.set_response("b" * 500)

    row = (await _rows(session))[0]
    assert row.request_text.startswith("a" * 50)
    assert "gekürzt" in row.request_text
    assert "gekürzt" in row.response_text
    assert len(row.request_text) < 500


@pytest.mark.asyncio
async def test_write_failure_does_not_break_the_call(session, monkeypatch):
    """Logging is observability — a broken write costs a log line, not a request."""

    def broken_maker():
        raise RuntimeError("DB ist weg")

    monkeypatch.setattr(ai_log_service, "async_session_maker", broken_maker)

    async with log_ai_call(kind="llm_analyze", provider="claude") as rec:
        rec.set_prompt("x")
        rec.set_response("y")

    assert await _rows(session) == []  # nothing written, but nothing raised either


@pytest.mark.asyncio
async def test_serialize_prompt_keeps_system_and_messages(session):
    """The system prompt is where the app's own behaviour lives; a log without it
    cannot explain why the model answered as it did."""
    text = serialize_prompt("Du bist ein Ernährungsexperte.", [{"role": "user", "content": "Müsli"}])
    assert "Ernährungsexperte" in text
    assert "Müsli" in text  # ensure_ascii=False keeps umlauts readable


# --- reading and pruning -----------------------------------------------------


@pytest.mark.asyncio
async def test_list_logs_filters_by_user_and_orders_newest_first(session):
    base = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    session.add_all(
        [
            AiRequestLog(
                user_id="alice", kind="llm_analyze", provider="claude",
                request_text="alt", latency_ms=1, created_at=base,
            ),
            AiRequestLog(
                user_id="alice", kind="llm_analyze", provider="claude",
                request_text="neu", latency_ms=1, created_at=base + timedelta(hours=2),
            ),
            AiRequestLog(
                user_id="bob", kind="llm_analyze", provider="claude",
                request_text="fremd", latency_ms=1, created_at=base,
            ),
        ]
    )
    await session.commit()

    rows = await list_logs_for_user(session, "alice")
    assert [r.request_text for r in rows] == ["neu", "alt"]

    assert len(await list_logs_for_user(session, "alice", limit=1)) == 1


# --- the user-facing view ----------------------------------------------------


def _row(**kw) -> AiRequestLog:
    defaults = dict(
        user_id="alice", kind="llm_analyze", provider="openai",
        request_text="", latency_ms=1, success=True,
    )
    return AiRequestLog(**{**defaults, **kw})


@pytest.mark.asyncio
async def test_user_view_hides_the_system_prompt(session):
    """The system prompt is internal — a user must see only their own words."""
    session.add(
        _row(
            request_text=serialize_prompt(
                "You are a nutrition analysis assistant. SECRET RULES",
                [{"role": "user", "content": "150g Skyr"}],
            ),
            response_text='{"type":"result","description":"150 g Skyr"}',
        )
    )
    await session.commit()

    entry = (await list_user_entries(session, "alice"))[0]
    assert entry.input_text == "150g Skyr"
    assert entry.output_text == "150 g Skyr"
    assert "SECRET RULES" not in entry.input_text
    assert "SECRET RULES" not in (entry.output_text or "")


@pytest.mark.asyncio
async def test_user_view_reads_transcript_question_and_ingredients(session):
    session.add_all(
        [
            _row(kind="transcribe", response_text="Zwei Eier"),
            _row(
                request_text=serialize_prompt("sys", [{"role": "user", "content": "Nudeln"}]),
                response_text='{"type":"question","question":"Welche Nudeln?"}',
            ),
            _row(
                kind="llm_ingredients",
                request_text=serialize_prompt("sys", [{"role": "user", "content": "Pasta und Öl"}]),
                response_text='```json\n[{"description":"Pasta"},{"description":"Öl"}]\n```',
            ),
        ]
    )
    await session.commit()

    by_kind = {e.kind: e for e in await list_user_entries(session, "alice")}
    assert by_kind["transcribe"].output_text == "Zwei Eier"
    assert by_kind["transcribe"].input_text == "🎤 Sprachaufnahme"
    assert by_kind["llm_analyze"].output_text == "Welche Nudeln?"
    # fenced JSON and an array both have to survive
    assert by_kind["llm_ingredients"].output_text == "Pasta, Öl"


@pytest.mark.asyncio
async def test_user_view_survives_unparseable_and_failed_rows(session):
    session.add_all(
        [
            _row(request_text="not json", response_text="not json either"),
            _row(
                request_text=serialize_prompt("sys", [{"role": "user", "content": "Apfel"}]),
                response_text=None, success=False, error="AuthenticationError: 401",
            ),
        ]
    )
    await session.commit()

    entries = await list_user_entries(session, "alice")
    assert len(entries) == 2
    failed = [e for e in entries if not e.success][0]
    assert failed.input_text == "Apfel"  # still shows what they asked
    assert failed.output_text is None  # and never leaks the raw error


@pytest.mark.asyncio
async def test_prune_drops_only_rows_past_retention(session):
    now = datetime.now(timezone.utc)
    session.add_all(
        [
            AiRequestLog(
                user_id="alice", kind="llm_analyze", provider="claude",
                request_text="alt", latency_ms=1, created_at=now - timedelta(days=91),
            ),
            AiRequestLog(
                user_id="alice", kind="llm_analyze", provider="claude",
                request_text="frisch", latency_ms=1, created_at=now - timedelta(days=1),
            ),
        ]
    )
    await session.commit()

    assert await prune_old_logs(session) == 1
    rows = await _rows(session)
    assert [r.request_text for r in rows] == ["frisch"]


# --- lifetime token counter --------------------------------------------------


@pytest.mark.asyncio
async def test_tokens_accumulate_into_lifetime_counter(session):
    set_ai_context("alice", "text", "/api/meals/text")
    async with log_ai_call(kind="llm_analyze", provider="claude") as rec:
        rec.set_prompt("x")
        rec.set_response("y", tokens_in=12, tokens_out=5)

    assert await get_token_totals(session, "alice") == (12, 5)

    async with log_ai_call(kind="llm_ingredients", provider="claude") as rec:
        rec.set_prompt("x")
        rec.set_response("y", tokens_in=8, tokens_out=3)

    assert await get_token_totals(session, "alice") == (20, 8)


@pytest.mark.asyncio
async def test_calls_without_tokens_leave_the_counter_untouched(session):
    """Transcription and failures carry no token usage, so they must not create
    or bump a counter row."""
    set_ai_context("bob", "voice", "/api/audio")
    async with log_ai_call(kind="transcribe", provider="openai") as rec:
        rec.set_prompt("<audio>")
        rec.set_response("Zwei Eier")  # no token counts

    with pytest.raises(RuntimeError):
        async with log_ai_call(kind="llm_analyze", provider="claude") as rec:
            rec.set_prompt("x")
            raise RuntimeError("weg")

    assert await get_token_totals(session, "bob") == (0, 0)


@pytest.mark.asyncio
async def test_anonymous_call_is_not_counted(session):
    """No user context means no counter to credit — the log row is enough."""
    async with log_ai_call(kind="llm_analyze", provider="claude") as rec:
        rec.set_prompt("x")
        rec.set_response("y", tokens_in=7, tokens_out=2)

    assert await token_totals_by_user(session) == {}


@pytest.mark.asyncio
async def test_totals_are_kept_per_user(session):
    for name, tin, tout in [("alice", 10, 4), ("bob", 3, 1), ("alice", 5, 2)]:
        set_ai_context(name, "text", "/api/meals/text")
        async with log_ai_call(kind="llm_analyze", provider="claude") as rec:
            rec.set_prompt("x")
            rec.set_response("y", tokens_in=tin, tokens_out=tout)

    assert await token_totals_by_user(session) == {"alice": (15, 6), "bob": (3, 1)}


@pytest.mark.asyncio
async def test_counter_survives_log_pruning(session):
    set_ai_context("alice", "text", "/api/meals/text")
    async with log_ai_call(kind="llm_analyze", provider="claude") as rec:
        rec.set_prompt("x")
        rec.set_response("y", tokens_in=12, tokens_out=5)

    # Age the log row past retention and prune it away.
    row = (await _rows(session))[0]
    row.created_at = datetime.now(timezone.utc) - timedelta(days=999)
    await session.commit()
    assert await prune_old_logs(session) == 1
    assert await _rows(session) == []

    # The lifetime counter is independent of the pruned rows.
    assert await get_token_totals(session, "alice") == (12, 5)
