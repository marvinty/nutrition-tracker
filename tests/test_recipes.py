"""Tests for the recipe service: building recipes, totals/per-portion, and
logging a portion into the meal diary.

Like test_clarification_flow, these exercise the service layer directly with an
in-memory SQLite database (no HTTP/auth stack). Config requires an API key at
import time, so we set dummy env vars before importing app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.meal import Meal  # noqa: F401 — register with Base.metadata
from app.models.recipe import Recipe, RecipeIngredient  # noqa: F401 — register with Base.metadata
from app.providers.base import NutritionResult, parse_ingredients
from app.schemas.recipe import RecipeCreate, RecipeUpdate
from app.services.meal_service import list_meals
from app.services.recipe_service import (
    add_ingredient_result,
    create_recipe,
    delete_ingredient,
    delete_recipe,
    get_recipe,
    list_recipes,
    log_recipe_portion,
    recipe_per_portion,
    recipe_totals,
    update_recipe,
)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _result(desc, cals, p, c, f):
    return NutritionResult(description=desc, calories=cals, protein=p, carbs=c, fat=f)


@pytest.mark.asyncio
async def test_totals_and_per_portion(session):
    recipe = await create_recipe(session, "tester", RecipeCreate(name="Bowl", servings=2))
    await add_ingredient_result(session, recipe, _result("200g rice", 260.0, 5.0, 57.0, 0.5))
    await add_ingredient_result(session, recipe, _result("150g chicken", 240.0, 45.0, 0.0, 5.0))

    recipe = await get_recipe(session, recipe.id, "tester")
    total = recipe_totals(recipe)
    assert (total.calories, total.protein, total.carbs, total.fat) == (500.0, 50.0, 57.0, 5.5)

    per = recipe_per_portion(recipe)
    # per-portion macros are rounded to 1 decimal (5.5g fat / 2 = 2.75 -> 2.8)
    assert (per.calories, per.protein, per.carbs, per.fat) == (250.0, 25.0, 28.5, 2.8)


@pytest.mark.asyncio
async def test_update_servings_changes_per_portion(session):
    recipe = await create_recipe(session, "tester", RecipeCreate(name="Bowl", servings=1))
    await add_ingredient_result(session, recipe, _result("stuff", 400.0, 40.0, 20.0, 10.0))

    updated = await update_recipe(session, recipe.id, "tester", RecipeUpdate(servings=4))
    assert updated.servings == 4
    per = recipe_per_portion(updated)
    assert per.calories == 100.0
    assert per.protein == 10.0


@pytest.mark.asyncio
async def test_servings_floored_to_one(session):
    recipe = await create_recipe(session, "tester", RecipeCreate(name="X", servings=0))
    assert recipe.servings == 1
    updated = await update_recipe(session, recipe.id, "tester", RecipeUpdate(servings=-3))
    assert updated.servings == 1


@pytest.mark.asyncio
async def test_log_portion_creates_meal(session):
    recipe = await create_recipe(session, "tester", RecipeCreate(name="Bolognese", servings=2))
    await add_ingredient_result(session, recipe, _result("sauce", 600.0, 30.0, 60.0, 20.0))
    recipe = await get_recipe(session, recipe.id, "tester")

    meal = await log_recipe_portion(session, "tester", recipe, portions=2, log_date=None)
    # per portion = 300/15/30/10; two portions = full recipe
    assert (meal.calories, meal.protein, meal.carbs, meal.fat) == (600.0, 30.0, 60.0, 20.0)
    assert "Bolognese" in meal.description
    assert "2 Portion" in meal.description

    meals = await list_meals(session, user_id="tester")
    assert len(meals) == 1


@pytest.mark.asyncio
async def test_delete_ingredient_and_recipe(session):
    recipe = await create_recipe(session, "tester", RecipeCreate(name="Bowl", servings=1))
    i1 = await add_ingredient_result(session, recipe, _result("a", 100.0, 1.0, 2.0, 3.0))
    await add_ingredient_result(session, recipe, _result("b", 50.0, 0.0, 0.0, 0.0))

    assert await delete_ingredient(session, recipe.id, i1.id, "tester") is True
    recipe = await get_recipe(session, recipe.id, "tester")
    assert recipe_totals(recipe).calories == 50.0

    assert await delete_recipe(session, recipe.id, "tester") is True
    assert await get_recipe(session, recipe.id, "tester") is None
    # ingredients removed via cascade
    remaining = (await session.execute(select(RecipeIngredient))).scalars().all()
    assert remaining == []


def test_parse_ingredients_splits_multiple():
    raw = (
        '[{"description": "200g pasta", "calories": 280, "protein": 10, "carbs": 56, "fat": 1.5},'
        ' {"description": "20g olive oil", "calories": 180, "protein": 0, "carbs": 0, "fat": 20}]'
    )
    results = parse_ingredients(raw, "200g pasta and 20g olive oil")
    assert [r.description for r in results] == ["200g pasta", "20g olive oil"]
    assert results[1].fat == 20


def test_parse_ingredients_with_fences_and_single_object():
    # A single ingredient may come back as one object rather than an array.
    raw = '```json\n{"description": "1 apple", "calories": 95, "protein": 0.5, "carbs": 25, "fat": 0.3}\n```'
    results = parse_ingredients(raw, "an apple")
    assert len(results) == 1
    assert results[0].description == "1 apple"
    assert results[0].calories == 95


def test_parse_ingredients_wrapper_key():
    raw = '{"ingredients": [{"description": "egg", "calories": 78}]}'
    results = parse_ingredients(raw, "egg")
    assert len(results) == 1 and results[0].description == "egg"


def test_parse_ingredients_unparseable_falls_back():
    results = parse_ingredients("not json", "some soup")
    assert len(results) == 1
    assert results[0].description == "some soup"
    assert results[0].calories is None


@pytest.mark.asyncio
async def test_user_isolation(session):
    recipe = await create_recipe(session, "alice", RecipeCreate(name="Secret", servings=1))
    assert await get_recipe(session, recipe.id, "bob") is None
    assert await list_recipes(session, "bob") == []
    assert await delete_recipe(session, recipe.id, "bob") is False
