from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import resolve_timestamp
from app.models.meal import Meal
from app.models.recipe import Recipe, RecipeIngredient
from app.providers.base import NutritionResult
from app.schemas.meal import MealCreate
from app.schemas.recipe import Macros, RecipeCreate, RecipeRead, RecipeUpdate
from app.services.meal_service import create_meal


async def create_recipe(session: AsyncSession, user_id: str, data: RecipeCreate) -> Recipe:
    recipe = Recipe(user_id=user_id, name=data.name, servings=max(data.servings, 1))
    session.add(recipe)
    await session.commit()
    await session.refresh(recipe)
    return recipe


async def get_recipe(session: AsyncSession, recipe_id: int, user_id: str) -> Optional[Recipe]:
    result = await session.execute(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_recipes(session: AsyncSession, user_id: str) -> list[Recipe]:
    result = await session.execute(
        select(Recipe).where(Recipe.user_id == user_id).order_by(Recipe.updated_at.desc())
    )
    return list(result.scalars().all())


async def update_recipe(
    session: AsyncSession, recipe_id: int, user_id: str, data: RecipeUpdate
) -> Optional[Recipe]:
    recipe = await get_recipe(session, recipe_id, user_id)
    if recipe is None:
        return None
    fields = data.model_dump(exclude_unset=True)
    if "servings" in fields and fields["servings"] is not None:
        fields["servings"] = max(int(fields["servings"]), 1)
    for field, value in fields.items():
        setattr(recipe, field, value)
    await session.commit()
    await session.refresh(recipe)
    return recipe


async def delete_recipe(session: AsyncSession, recipe_id: int, user_id: str) -> bool:
    recipe = await get_recipe(session, recipe_id, user_id)
    if recipe is None:
        return False
    await session.delete(recipe)
    await session.commit()
    return True


async def add_ingredient_result(
    session: AsyncSession, recipe: Recipe, result: NutritionResult
) -> RecipeIngredient:
    """Persist an LLM NutritionResult as a recipe ingredient.

    This is the shared write path used by the text/audio recipe-mode endpoints,
    and the intended entry point for future voice-command recipe editing (an
    "add ingredient" command would land here).
    """
    ingredient = RecipeIngredient(
        recipe_id=recipe.id,
        description=result.description,
        calories=result.calories,
        protein=result.protein,
        carbs=result.carbs,
        fat=result.fat,
    )
    session.add(ingredient)
    await session.commit()
    await session.refresh(recipe)
    return ingredient


async def delete_ingredient(
    session: AsyncSession, recipe_id: int, ingredient_id: int, user_id: str
) -> bool:
    recipe = await get_recipe(session, recipe_id, user_id)
    if recipe is None:
        return False
    result = await session.execute(
        select(RecipeIngredient).where(
            RecipeIngredient.id == ingredient_id,
            RecipeIngredient.recipe_id == recipe_id,
        )
    )
    ingredient = result.scalar_one_or_none()
    if ingredient is None:
        return False
    await session.delete(ingredient)
    await session.commit()
    # Session uses expire_on_commit=False, so refresh the cached collection
    # otherwise the deleted ingredient still shows in recipe.ingredients.
    await session.refresh(recipe, ["ingredients"])
    return True


def recipe_totals(recipe: Recipe) -> Macros:
    total = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for ing in recipe.ingredients:
        total["calories"] += ing.calories or 0
        total["protein"] += ing.protein or 0
        total["carbs"] += ing.carbs or 0
        total["fat"] += ing.fat or 0
    return Macros(**{k: round(v, 1) for k, v in total.items()})


def recipe_per_portion(recipe: Recipe) -> Macros:
    servings = max(recipe.servings or 1, 1)
    total = recipe_totals(recipe)
    return Macros(
        calories=round(total.calories / servings, 1),
        protein=round(total.protein / servings, 1),
        carbs=round(total.carbs / servings, 1),
        fat=round(total.fat / servings, 1),
    )


def to_recipe_read(recipe: Recipe) -> RecipeRead:
    return RecipeRead(
        id=recipe.id,
        name=recipe.name,
        servings=recipe.servings,
        ingredients=list(recipe.ingredients),
        total=recipe_totals(recipe),
        per_portion=recipe_per_portion(recipe),
    )


async def log_recipe_portion(
    session: AsyncSession,
    user_id: str,
    recipe: Recipe,
    portions: float,
    log_date: Optional[date],
) -> Meal:
    per = recipe_per_portion(recipe)
    portion_label = f"{portions:g}"
    meal = await create_meal(
        session,
        MealCreate(
            user_id=user_id,
            description=f"{recipe.name} ({portion_label} Portion)",
            calories=round(per.calories * portions, 1),
            protein=round(per.protein * portions, 1),
            carbs=round(per.carbs * portions, 1),
            fat=round(per.fat * portions, 1),
            timestamp=resolve_timestamp(log_date),
        ),
    )
    return meal
