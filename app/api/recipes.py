from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.time import resolve_timestamp
from app.db.session import get_session
from app.models.user import User
from app.providers import get_provider
from app.providers.base import LLMProvider
from app.schemas.meal import MealRead
from app.schemas.recipe import (
    IngredientTextInput,
    LogPortionRequest,
    RecipeCreate,
    RecipeRead,
    RecipeUpdate,
)
from app.services.audio_service import transcribe_audio
from app.services.recipe_service import (
    add_ingredient_result,
    create_recipe,
    delete_ingredient,
    delete_recipe,
    get_recipe,
    list_recipes,
    log_recipe_portion,
    to_recipe_read,
    update_recipe,
)

# JSON API is namespaced under /api to avoid colliding with the /recipes HTML page.
router = APIRouter(prefix="/api/recipes", tags=["recipes"])


async def _require_recipe(session: AsyncSession, recipe_id: int, user_id: str):
    recipe = await get_recipe(session, recipe_id, user_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.post("", response_model=RecipeRead, status_code=201)
async def new_recipe(
    body: RecipeCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RecipeRead:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name must not be empty")
    recipe = await create_recipe(session, user.username, body)
    return to_recipe_read(recipe)


@router.get("", response_model=list[RecipeRead])
async def get_recipes(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[RecipeRead]:
    recipes = await list_recipes(session, user.username)
    return [to_recipe_read(r) for r in recipes]


@router.get("/{recipe_id}", response_model=RecipeRead)
async def get_one_recipe(
    recipe_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RecipeRead:
    recipe = await _require_recipe(session, recipe_id, user.username)
    return to_recipe_read(recipe)


@router.patch("/{recipe_id}", response_model=RecipeRead)
async def edit_recipe(
    recipe_id: int,
    body: RecipeUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RecipeRead:
    recipe = await update_recipe(session, recipe_id, user.username, body)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return to_recipe_read(recipe)


@router.delete("/{recipe_id}", status_code=204)
async def remove_recipe(
    recipe_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    if not await delete_recipe(session, recipe_id, user.username):
        raise HTTPException(status_code=404, detail="Recipe not found")


async def _add_ingredient(
    provider: LLMProvider, session: AsyncSession, recipe, text: str
) -> None:
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Ingredient text must not be empty")
    # A single utterance may name several ingredients ("200g pasta and 20g olive
    # oil"); extract_ingredients splits them so each is tracked separately. It
    # always estimates (never asks), which is what we want while cooking.
    results = await provider.extract_ingredients(text)
    for result in results:
        await add_ingredient_result(session, recipe, result)


@router.post("/{recipe_id}/ingredients/text", response_model=RecipeRead)
async def add_ingredient_text(
    recipe_id: int,
    body: IngredientTextInput,
    session: AsyncSession = Depends(get_session),
    provider: LLMProvider = Depends(get_provider),
    user: User = Depends(get_current_user),
) -> RecipeRead:
    recipe = await _require_recipe(session, recipe_id, user.username)
    try:
        await _add_ingredient(provider, session, recipe, body.text)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {exc}") from exc
    return to_recipe_read(recipe)


@router.post("/{recipe_id}/ingredients/audio", response_model=RecipeRead)
async def add_ingredient_audio(
    recipe_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    provider: LLMProvider = Depends(get_provider),
    user: User = Depends(get_current_user),
) -> RecipeRead:
    recipe = await _require_recipe(session, recipe_id, user.username)
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")
    try:
        transcript = await transcribe_audio(audio_bytes, file.filename or "audio.wav")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Whisper transcription failed: {exc}") from exc
    try:
        await _add_ingredient(provider, session, recipe, transcript)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {exc}") from exc
    return to_recipe_read(recipe)


@router.delete("/{recipe_id}/ingredients/{ingredient_id}", status_code=204)
async def remove_ingredient(
    recipe_id: int,
    ingredient_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    if not await delete_ingredient(session, recipe_id, ingredient_id, user.username):
        raise HTTPException(status_code=404, detail="Ingredient not found")


@router.post("/{recipe_id}/log", response_model=MealRead, status_code=201)
async def log_portion(
    recipe_id: int,
    body: LogPortionRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> MealRead:
    if body.portions <= 0:
        raise HTTPException(status_code=400, detail="Portions must be greater than 0")
    recipe = await _require_recipe(session, recipe_id, user.username)
    try:
        resolve_timestamp(body.log_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    meal = await log_recipe_portion(session, user.username, recipe, body.portions, body.log_date)
    return meal
