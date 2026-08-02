"""Tests for ``cost_service`` — the euro figures behind /admin/costs.

The point of this module is a number you can base a price on, so most of these
tests are about the ways such a number goes quietly wrong: a model with no price
counted as free, a transcription with no recorded duration counted as free, a call
bucketed onto the wrong day because the timestamp is UTC and the day is Berlin.
Each of those would produce a total that looks fine and is too small.

Prices are pinned via monkeypatch rather than taken from the shipped config, so
these stay green when a provider changes its rates.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.money import eur_bucket
from app.models.ai_request_log import AiRequestLog
from app.models.base import Base
from app.services.cost_service import CostBucket, call_cost_eur, collect_costs

# Round numbers so every expected value below can be checked by hand.
_PRICES = {"test-llm": {"in": 10.0, "out": 20.0}}
_AUDIO_PRICES = {"test-whisper": 6.0}  # USD per minute


@pytest.fixture(autouse=True)
def prices(monkeypatch):
    """A rate of 1.0 and no VAT by default: the conversion has its own test, and
    leaving it out of the others keeps their expected values readable."""
    monkeypatch.setattr(settings, "model_prices_usd", _PRICES)
    monkeypatch.setattr(settings, "audio_prices_usd_per_minute", _AUDIO_PRICES)
    monkeypatch.setattr(settings, "usd_to_eur", 1.0)
    monkeypatch.setattr(settings, "price_vat_rate", 0.0)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _log(**kw) -> AiRequestLog:
    defaults = dict(
        user_id="alice",
        kind="llm_analyze",
        provider="openai",
        model="test-llm",
        request_text="x",
        latency_ms=1,
        success=True,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(kw)
    return AiRequestLog(**defaults)


# --- pricing a single call -------------------------------------------------


def test_prices_an_llm_call_from_its_token_counts():
    # 1M in at $10 + 0.5M out at $20 = $20
    assert call_cost_eur(
        model="test-llm",
        provider="openai",
        prompt_tokens=1_000_000,
        completion_tokens=500_000,
        audio_seconds=None,
    ) == pytest.approx(20.0)


def test_prices_a_transcription_by_the_minute():
    # 30s at $6/min = $3
    assert call_cost_eur(
        model="test-whisper",
        provider="openai",
        prompt_tokens=None,
        completion_tokens=None,
        audio_seconds=30.0,
    ) == pytest.approx(3.0)


def test_an_unknown_model_is_unpriced_not_free():
    """The failure this whole module guards against: a new model silently priced at
    zero shrinks the total exactly where someone is about to trust it."""
    assert (
        call_cost_eur(
            model="some-new-model",
            provider="openai",
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            audio_seconds=None,
        )
        is None
    )


def test_a_transcription_without_a_duration_is_unpriced_not_free():
    """Every transcription logged before the audio_seconds column existed. The price
    is known, the quantity is not — which is not the same as costing nothing."""
    assert (
        call_cost_eur(
            model="test-whisper",
            provider="openai",
            prompt_tokens=None,
            completion_tokens=None,
            audio_seconds=None,
        )
        is None
    )


def test_a_failed_call_on_a_priced_model_costs_zero():
    """Distinct from the two cases above: the provider reported no usage because the
    call never got that far. That is a real zero, not a gap in our data."""
    assert (
        call_cost_eur(
            model="test-llm",
            provider="openai",
            prompt_tokens=None,
            completion_tokens=None,
            audio_seconds=None,
        )
        == 0.0
    )


def test_the_local_provider_is_free():
    """Runs in-process. Without the explicit branch its model name ("base") would
    fall through to unpriced and raise a warning about a genuinely free call."""
    assert (
        call_cost_eur(
            model="base",
            provider="local",
            prompt_tokens=None,
            completion_tokens=None,
            audio_seconds=12.0,
        )
        == 0.0
    )


def test_applies_the_exchange_rate_and_vat(monkeypatch):
    monkeypatch.setattr(settings, "usd_to_eur", 0.5)
    monkeypatch.setattr(settings, "price_vat_rate", 0.19)
    # $10 -> 10 * 0.5 * 1.19
    assert call_cost_eur(
        model="test-llm",
        provider="openai",
        prompt_tokens=1_000_000,
        completion_tokens=0,
        audio_seconds=None,
    ) == pytest.approx(5.95)


# --- aggregation -----------------------------------------------------------


@pytest.mark.asyncio
async def test_totals_split_by_user_and_by_model(session):
    session.add_all(
        [
            _log(user_id="alice", prompt_tokens=1_000_000, completion_tokens=0),
            _log(user_id="alice", prompt_tokens=1_000_000, completion_tokens=0),
            _log(user_id="bob", prompt_tokens=500_000, completion_tokens=0),
            _log(
                user_id="bob",
                kind="transcribe",
                model="test-whisper",
                prompt_tokens=None,
                completion_tokens=None,
                audio_seconds=60.0,  # 1 min at $6
            ),
        ]
    )
    await session.commit()

    report = await collect_costs(session)

    assert report.total.eur == pytest.approx(10 + 10 + 5 + 6)
    by_user = report.buckets_by_user()
    assert by_user["alice"].eur == pytest.approx(20.0)
    assert by_user["bob"].eur == pytest.approx(11.0)
    # Dearest first, so the expensive user is the one you see.
    assert [u.username for u in report.by_user] == ["alice", "bob"]

    by_model = {m.model: m for m in report.by_model}
    assert by_model["test-llm"].calls == 3
    assert by_model["test-whisper"].audio_seconds == pytest.approx(60.0)


@pytest.mark.asyncio
async def test_unpriced_calls_are_counted_and_named(session):
    session.add_all(
        [
            _log(prompt_tokens=1_000_000, completion_tokens=0),
            _log(model="mystery-model", prompt_tokens=9_000_000, completion_tokens=0),
        ]
    )
    await session.commit()

    report = await collect_costs(session)

    assert report.unpriced == {"mystery-model": 1}
    assert report.total.unpriced_calls == 1
    assert report.total.is_complete is False
    # The priced half is still reported — the figure is a lower bound, not nothing.
    assert report.total.eur == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_days_are_bucketed_in_local_time_not_utc(session, monkeypatch):
    """23:30 UTC is already the next day in Berlin. Grouping with SQL's DATE() would
    put this call on the previous day and misreport every late-evening meal."""
    monkeypatch.setattr(settings, "app_timezone", "Europe/Berlin")
    # 2026-07-14 23:30 UTC == 2026-07-15 01:30 Berlin (CEST, UTC+2)
    late = datetime(2026, 7, 14, 23, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "app.services.cost_service.today_local", lambda: late.date() + timedelta(days=1)
    )
    session.add(_log(created_at=late, prompt_tokens=1_000_000, completion_tokens=0))
    await session.commit()

    report = await collect_costs(session, days=30)

    assert [d.day for d in report.by_day] == [late.date() + timedelta(days=1)]
    # And it counts as "today" relative to that local date, not yesterday.
    assert report.today.eur == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_calls_older_than_the_window_are_excluded(session):
    session.add_all(
        [
            _log(prompt_tokens=1_000_000, completion_tokens=0),
            _log(
                created_at=datetime.now(timezone.utc) - timedelta(days=45),
                prompt_tokens=1_000_000,
                completion_tokens=0,
            ),
        ]
    )
    await session.commit()

    report = await collect_costs(session, days=30)

    assert report.total.calls == 1
    assert report.total.eur == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_calls_without_a_user_still_count_toward_the_total(session):
    """A call made outside a request context has no username but still costs money,
    so it gets its own bucket rather than being dropped from the report."""
    session.add(_log(user_id=None, prompt_tokens=1_000_000, completion_tokens=0))
    await session.commit()

    report = await collect_costs(session)

    assert report.total.eur == pytest.approx(10.0)
    assert report.by_user[0].username == "(ohne Nutzer)"


@pytest.mark.asyncio
async def test_projection_is_none_without_any_calls(session):
    report = await collect_costs(session)
    assert report.projected_30_days is None
    assert report.total.eur == 0.0


# --- how a partial figure is presented -------------------------------------


@pytest.mark.asyncio
async def test_per_call_average_divides_by_priced_calls_only(session):
    """The per-call figure is what a free-tier limit gets derived from, so dividing
    a partial sum by the full call count — understating it — is the wrong default."""
    session.add_all(
        [
            _log(prompt_tokens=1_000_000, completion_tokens=0),  # 10
            _log(model="mystery-model", prompt_tokens=1_000_000, completion_tokens=0),
        ]
    )
    await session.commit()

    bucket = (await collect_costs(session)).buckets_by_user()["alice"]

    assert bucket.calls == 2
    assert bucket.unpriced_calls == 1
    # 10 / 1 priced call, not 10 / 2.
    assert bucket.eur_per_priced_call == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_per_call_average_is_none_when_nothing_could_be_priced(session):
    session.add(_log(model="mystery-model", prompt_tokens=1_000, completion_tokens=0))
    await session.commit()

    bucket = (await collect_costs(session)).buckets_by_user()["alice"]

    assert bucket.eur_per_priced_call is None


def test_eur_bucket_distinguishes_complete_partial_and_unknown():
    """The three cases the admin templates must never collapse: a fully priced sum,
    a lower bound, and a bucket where nothing could be priced — which has to read as
    "unbekannt" rather than a confident 0,0000 €."""
    complete = CostBucket(calls=2, eur=1.5)
    partial = CostBucket(calls=2, eur=1.5, unpriced_calls=1)
    unknown = CostBucket(calls=2, eur=0.0, unpriced_calls=2)

    assert eur_bucket(complete) == "1,5000 €"
    assert eur_bucket(partial) == "mind. 1,5000 €"
    assert eur_bucket(unknown) == "unbekannt"


def test_headline_scales_precision_to_the_amount():
    """Fractions of a cent early on, plain money later — a young install would
    otherwise show "0,00 €" for spend that is real."""
    assert eur_bucket(CostBucket(calls=1, eur=0.0018), digits=None) == "0,0018 €"
    assert eur_bucket(CostBucket(calls=1, eur=12.3456), digits=None) == "12,35 €"
