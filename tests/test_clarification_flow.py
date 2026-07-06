"""Tests for the clarifying-question flow (run_analysis) and response parsing.

These exercise the service layer directly with a fake provider and an in-memory
SQLite database, avoiding the HTTP/auth stack. Config requires an API key to be
present at import time, so we set dummy env vars before importing app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.meal import Meal  # noqa: F401 — register with Base.metadata
from app.models.user import User
from app.providers.base import (
    ClarificationNeeded,
    NutritionResult,
    parse_analysis,
)
from app.services.meal_service import list_meals
from app.services.nutrition_flow import run_analysis


class FakeProvider:
    """Returns queued results in order; records the allow_questions flag seen."""

    def __init__(self, results):
        self._results = list(results)
        self.allow_questions_seen = []

    async def analyze(self, messages, allow_questions):
        self.allow_questions_seen.append(allow_questions)
        return self._results.pop(0)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def user():
    return User(username="tester")


@pytest.mark.asyncio
async def test_first_call_asks_and_saves_nothing(session, user):
    provider = FakeProvider([ClarificationNeeded(question="How much rice?")])
    messages = [{"role": "user", "content": "some rice"}]

    resp = await run_analysis(provider, session, user, messages, log_date=None)

    assert resp.status == "needs_clarification"
    assert resp.question == "How much rice?"
    # The assistant question is appended to the returned conversation.
    assert resp.messages[-1].role == "assistant"
    assert resp.messages[-1].content == "How much rice?"
    assert provider.allow_questions_seen == [True]
    assert await list_meals(session, user_id="tester") == []


@pytest.mark.asyncio
async def test_clarify_answer_saves_meal(session, user):
    provider = FakeProvider(
        [NutritionResult("200g rice", calories=260.0, protein=5.0, carbs=57.0, fat=0.5)]
    )
    messages = [
        {"role": "user", "content": "some rice"},
        {"role": "assistant", "content": "How much rice?"},
        {"role": "user", "content": "about 200 grams"},
    ]

    resp = await run_analysis(provider, session, user, messages, log_date=None)

    assert resp.status == "complete"
    assert resp.meal is not None
    assert resp.meal.calories == 260.0
    meals = await list_meals(session, user_id="tester")
    assert len(meals) == 1
    assert meals[0].description == "200g rice"


@pytest.mark.asyncio
async def test_forced_estimate_after_two_questions(session, user):
    # Two assistant turns already present -> allow_questions must be False, and
    # even if the provider tries to ask again we save an estimate.
    provider = FakeProvider(
        [NutritionResult("a snack", calories=150.0, protein=2.0, carbs=20.0, fat=6.0)]
    )
    messages = [
        {"role": "user", "content": "a snack"},
        {"role": "assistant", "content": "What was it?"},
        {"role": "user", "content": "not sure"},
        {"role": "assistant", "content": "Roughly how big?"},
        {"role": "user", "content": "no idea"},
    ]

    resp = await run_analysis(provider, session, user, messages, log_date=None)

    assert provider.allow_questions_seen == [False]
    assert resp.status == "complete"
    assert len(await list_meals(session, user_id="tester")) == 1


def test_parse_analysis_question():
    messages = [{"role": "user", "content": "rice"}]
    raw = '{"type": "question", "question": "How much?"}'
    result = parse_analysis(raw, messages, allow_questions=True)
    assert isinstance(result, ClarificationNeeded)
    assert result.question == "How much?"


def test_parse_analysis_result_with_fences():
    messages = [{"role": "user", "content": "rice"}]
    raw = '```json\n{"type": "result", "description": "rice", "calories": 200, "protein": 4, "carbs": 44, "fat": 0.4}\n```'
    result = parse_analysis(raw, messages, allow_questions=True)
    assert isinstance(result, NutritionResult)
    assert result.calories == 200
    assert result.description == "rice"


def test_parse_analysis_question_ignored_on_final_round():
    messages = [{"role": "user", "content": "rice"}]
    raw = '{"type": "question", "question": "How much?"}'
    result = parse_analysis(raw, messages, allow_questions=False)
    # A question on the final round degrades to a best-effort (null macros) result.
    assert isinstance(result, NutritionResult)
    assert result.description == "rice"
    assert result.calories is None


def test_parse_analysis_unparseable_falls_back():
    messages = [{"role": "user", "content": "rice"}]
    result = parse_analysis("not json at all", messages, allow_questions=True)
    assert isinstance(result, NutritionResult)
    assert result.description == "rice"
