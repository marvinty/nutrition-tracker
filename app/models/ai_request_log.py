from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from app.models.base import Base


class AiRequestLog(Base):
    """One row per outgoing AI call — LLM analysis, ingredient extraction, or
    transcription.

    Distinct from ``AiUsage``, which aggregates credits into a single row per user
    per day and therefore cannot answer what was actually asked, which model
    answered, or why a call failed. This table is the record of individual calls;
    a voice log produces two rows (``transcribe`` + ``llm_analyze``), matching the
    fact that it pays for two API calls.

    Privacy: ``request_text`` and ``response_text`` hold verbatim user input —
    meal descriptions and voice transcripts. Three things justify keeping them:
    the rows are reachable only from the admin panel, each text is capped at
    ``settings.ai_log_max_text_chars``, and ``prune_old_logs`` drops everything
    past ``settings.ai_log_retention_days`` at every boot.

    Failures are recorded too (``success`` false, ``error`` set). Before this
    table a provider outage surfaced only as an HTTP 502 to the client and left
    nothing behind on the server.
    """

    id = Column(Integer, primary_key=True, index=True)
    # Username, matching the Meal/AiUsage convention — a String, not a FK to user.id.
    # Nullable because a call made outside a request context (a script, a future
    # background job) should still be recorded rather than dropped.
    user_id = Column(String, nullable=True, index=True)
    # Credit action that paid for this call: "text" | "clarify" | "voice".
    action = Column(String, nullable=True, index=True)
    # What kind of call this was: "llm_analyze" | "llm_ingredients" | "transcribe".
    kind = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # "claude" | "openai" | "local"
    model = Column(String, nullable=True)  # e.g. "claude-3-5-haiku-20241022"
    endpoint = Column(String, nullable=True)  # request path, e.g. "/api/meals/text"
    # What was sent: the system prompt plus the conversation as JSON, or a
    # placeholder describing the audio for transcription calls.
    request_text = Column(Text, nullable=False)
    # The raw model output *before* parsing, which is what makes a bad parse
    # diagnosable. Null when the call failed before producing one.
    response_text = Column(Text, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    error = Column(String, nullable=True)
    # Indexed because it drives both queries this table has: the per-user list
    # (ordered by it) and pruning (filtered on it).
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
