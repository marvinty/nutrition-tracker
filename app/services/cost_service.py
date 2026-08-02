"""What the AI actually costs, in euros, aggregated out of the AI log.

Every price decision after this one — the free limit, the pro price, whether a
lifetime tier is survivable — rests on a number instead of a feeling, so the
guiding rule here is that the number must never be quietly too small. That is why
pricing returns ``Optional[float]`` and never falls back to ``0.0``: a model with
no entry in ``settings.model_prices_usd`` is *unpriced*, not free, and the report
carries the count of such calls so the page can say so out loud.

Costs are computed at read time rather than stored on the row. Freezing the price
into ``airequestlog`` would be more faithful to history, but it is the wrong trade
while the price table is still being calibrated: a corrected rate or a new exchange
rate should apply retroactively, without a migration and a backfill.

The window is bounded by ``settings.ai_log_retention_days`` — the log is pruned at
every boot, so there is no such thing as a lifetime cost here, and the admin page
labels the window rather than implying one.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.time import day_bounds, to_local, today_local
from app.models.ai_request_log import AiRequestLog

# Providers publish per-million-token prices; the log counts single tokens.
_TOKENS_PER_PRICE_UNIT = 1_000_000
_SECONDS_PER_MINUTE = 60
# Runs in-process (see providers/whisper/local.py), so it bills nothing. Without
# this its model name ("base") would fall through to the unpriced branch and raise
# a warning on the admin page about a call that genuinely cost zero.
_FREE_PROVIDER = "local"
# Reporting window shared by the cost page and the euro columns on the user pages,
# so the two never quote different periods for the same user.
DEFAULT_WINDOW_DAYS = 30


@dataclass
class CostBucket:
    """One row of any of the three breakdowns — per day, per user, per model.

    ``unpriced_calls`` is carried alongside ``eur`` on purpose: a bucket whose sum
    is incomplete has to be able to say so, otherwise the page presents a partial
    total as a whole one.
    """

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    audio_seconds: float = 0.0
    eur: float = 0.0
    unpriced_calls: int = 0

    def add(self, cost: Optional[float], row) -> None:
        self.calls += 1
        self.prompt_tokens += row.prompt_tokens or 0
        self.completion_tokens += row.completion_tokens or 0
        self.audio_seconds += row.audio_seconds or 0.0
        if cost is None:
            self.unpriced_calls += 1
        else:
            self.eur += cost

    @property
    def is_complete(self) -> bool:
        return self.unpriced_calls == 0

    @property
    def eur_per_priced_call(self) -> Optional[float]:
        """Average over the calls that could actually be priced, not over all of
        them. Dividing a partial sum by the full call count would understate the
        per-call cost exactly when some calls are missing a price — and the per-call
        figure is the one a free-tier limit gets derived from."""
        priced = self.calls - self.unpriced_calls
        return self.eur / priced if priced else None


@dataclass
class ModelCost(CostBucket):
    """A per-model bucket, which needs to name the model and its provider."""

    model: Optional[str] = None
    provider: str = ""


@dataclass
class DayCost(CostBucket):
    day: Optional[date] = None


@dataclass
class UserCost(CostBucket):
    username: Optional[str] = None


@dataclass
class CostReport:
    """Everything /admin/costs renders, from a single pass over the log."""

    window_days: int
    total: CostBucket = field(default_factory=CostBucket)
    today: CostBucket = field(default_factory=CostBucket)
    last_7_days: CostBucket = field(default_factory=CostBucket)
    by_day: list = field(default_factory=list)  # newest first
    by_user: list = field(default_factory=list)  # dearest first
    by_model: list = field(default_factory=list)  # dearest first
    # Model name -> number of calls we could not price. Drives the warning banner.
    unpriced: dict = field(default_factory=dict)

    def buckets_by_user(self) -> dict:
        """Username -> bucket, for the admin pages that show one user at a time."""
        return {row.username: row for row in self.by_user}

    @property
    def projected_30_days(self) -> Optional[float]:
        """The window's spend scaled to 30 days — the shape a monthly bill takes.

        None while the window holds less than a full day, where scaling a few hours
        up by 30 would produce a confident-looking number built on noise.
        """
        if self.window_days < 1 or self.total.calls == 0:
            return None
        return self.total.eur / self.window_days * 30


def _to_eur(usd: float) -> float:
    """Providers invoice in USD, and without a VAT ID the tax on that invoice is a
    real cost — so the euro figure is gross by default (``price_vat_rate``)."""
    return usd * settings.usd_to_eur * (1 + settings.price_vat_rate)


def call_cost_eur(
    *,
    model: Optional[str],
    provider: Optional[str],
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    audio_seconds: Optional[float],
) -> Optional[float]:
    """What one logged call cost, or None when it cannot be priced.

    None and 0.0 mean different things and must not be collapsed. 0.0 is a call we
    priced and that genuinely cost nothing — a local transcription, or an LLM call
    that failed before reporting any usage. None is a call we could not price at
    all: an unknown model, or a transcription from before ``audio_seconds`` was
    recorded. Returning 0.0 for those would understate the total silently, which is
    the one failure mode this whole module exists to avoid.
    """
    if provider == _FREE_PROVIDER:
        return 0.0

    token_price = settings.model_prices_usd.get(model or "")
    if token_price is not None:
        # Missing token counts on a priced model mean no usage was billed — a call
        # that failed before the provider reported any. That is a real zero.
        usd = (prompt_tokens or 0) / _TOKENS_PER_PRICE_UNIT * token_price["in"]
        usd += (completion_tokens or 0) / _TOKENS_PER_PRICE_UNIT * token_price["out"]
        return _to_eur(usd)

    minute_price = settings.audio_prices_usd_per_minute.get(model or "")
    if minute_price is not None:
        # Here a missing quantity is *not* a zero: the price is known, the duration
        # simply was never recorded (every transcription row predating the
        # audio_seconds column). Report it as unpriced rather than as free.
        if audio_seconds is None:
            return None
        return _to_eur(audio_seconds / _SECONDS_PER_MINUTE * minute_price)

    return None


async def collect_costs(
    session: AsyncSession, days: int = DEFAULT_WINDOW_DAYS
) -> CostReport:
    """Aggregate the last ``days`` local days of AI calls into euros.

    One query, selected column by column rather than as whole ORM rows:
    ``request_text`` and ``response_text`` may each hold
    ``settings.ai_log_max_text_chars`` (20k) characters, and loading a megabyte of
    prompt text to sum some integers would be a waste on every page view.

    Days are bucketed in Python via ``to_local``, not by SQL's ``DATE()``. The
    column stores UTC, so ``DATE(created_at)`` would push every call made between
    midnight and 02:00 Berlin time onto the previous day — exactly the boundary
    ``core.time`` exists to get right.
    """
    first_day = today_local() - timedelta(days=days - 1)
    start_utc, _ = day_bounds(first_day)
    # Naive UTC to compare against what SQLite hands back; mixing an aware value
    # into the WHERE clause raises. Same reasoning as ai_log_service.prune_old_logs.
    cutoff = start_utc.replace(tzinfo=None)

    rows = (
        await session.execute(
            select(
                AiRequestLog.created_at,
                AiRequestLog.model,
                AiRequestLog.provider,
                AiRequestLog.user_id,
                AiRequestLog.prompt_tokens,
                AiRequestLog.completion_tokens,
                AiRequestLog.audio_seconds,
            ).where(AiRequestLog.created_at >= cutoff)
        )
    ).all()

    report = CostReport(window_days=days)
    today = today_local()
    week_start = today - timedelta(days=6)
    days_map: dict = {}
    users_map: dict = {}
    models_map: dict = {}

    for row in rows:
        cost = call_cost_eur(
            model=row.model,
            provider=row.provider,
            prompt_tokens=row.prompt_tokens,
            completion_tokens=row.completion_tokens,
            audio_seconds=row.audio_seconds,
        )
        report.total.add(cost, row)
        if cost is None:
            key = row.model or "(ohne Modell)"
            report.unpriced[key] = report.unpriced.get(key, 0) + 1

        local_day = to_local(row.created_at).date()
        if local_day == today:
            report.today.add(cost, row)
        if local_day >= week_start:
            report.last_7_days.add(cost, row)

        days_map.setdefault(local_day, DayCost(day=local_day)).add(cost, row)
        # Calls made outside a request context carry no username; they still cost
        # money, so they get their own bucket rather than being dropped.
        username = row.user_id or "(ohne Nutzer)"
        users_map.setdefault(username, UserCost(username=username)).add(cost, row)
        model_key = (row.model, row.provider)
        models_map.setdefault(
            model_key, ModelCost(model=row.model, provider=row.provider)
        ).add(cost, row)

    report.by_day = sorted(days_map.values(), key=lambda b: b.day, reverse=True)
    report.by_user = sorted(users_map.values(), key=lambda b: b.eur, reverse=True)
    report.by_model = sorted(models_map.values(), key=lambda b: b.eur, reverse=True)
    return report
