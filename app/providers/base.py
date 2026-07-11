import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class NutritionResult:
    description: str
    calories: Optional[float]
    protein: Optional[float]
    carbs: Optional[float]
    fat: Optional[float]


@dataclass
class ClarificationNeeded:
    question: str


AnalysisResult = Union[NutritionResult, ClarificationNeeded]


_JSON_SHAPE = """{
  "type": "result",
  "description": "...",
  "calories": 0.0,
  "protein": 0.0,
  "carbs": 0.0,
  "fat": 0.0
}"""

_QUESTION_SHAPE = """{"type": "question", "question": "..."}"""

_INGREDIENTS_SHAPE = """[
  {"description": "...", "calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
]"""


def build_system_prompt(allow_questions: bool) -> str:
    """System prompt for the nutrition analysis conversation.

    When ``allow_questions`` is True the model may ask ONE short clarifying
    question if it cannot estimate sensible macros. When False (the final round)
    it must always return an estimate and never ask.
    """
    base = (
        "You are a nutrition analysis assistant.\n"
        "The user describes food they have eaten (typed or transcribed from speech).\n"
        "Your job is to return structured nutrition data: description, calories, "
        "protein, carbs, fat (grams for macros, kcal for calories).\n"
        "Respond ONLY with a single valid JSON object and no text outside it.\n"
    )
    if allow_questions:
        return base + (
            "\nIf the description is too vague to estimate sensible macros "
            "(missing food, portion size, or preparation), ask ONE short, specific "
            "follow-up question instead of guessing. Use this shape:\n"
            f"{_QUESTION_SHAPE}\n"
            "\nOtherwise, return the nutrition result using this shape:\n"
            f"{_JSON_SHAPE}\n"
            "Only ask a question when it would materially change the estimate. "
            "If you already have enough to estimate, return a result."
        )
    return base + (
        "\nYou must return a nutrition result now and MUST NOT ask any question. "
        "Estimate any missing amounts to the best of your knowledge using typical "
        "portion sizes. Never leave a macro null just because you are unsure. "
        "Use this shape:\n"
        f"{_JSON_SHAPE}"
    )


def build_ingredients_prompt() -> str:
    """System prompt for extracting one or more recipe ingredients at once.

    Used by recipe mode: the user may name several ingredients in a single
    utterance (e.g. "200g pasta and 20g olive oil"), which must be returned as
    separate entries so they are tracked individually.
    """
    return (
        "You extract recipe ingredients from a single utterance (typed or transcribed from speech).\n"
        "The user may name ONE or SEVERAL ingredients at once, e.g. \"200g pasta and 20g olive oil\".\n"
        "Split them into SEPARATE ingredients: one array entry per distinct ingredient the user named.\n"
        "Do NOT decompose a single named dish (e.g. \"spaghetti bolognese\") into its components — "
        "keep that as one entry.\n"
        "For each ingredient estimate its nutrition (grams for protein/carbs/fat, kcal for calories) "
        "from the stated amount and typical values. Never ask questions; always estimate.\n"
        "Respond ONLY with a single valid JSON array and no text outside it, using this shape:\n"
        f"{_INGREDIENTS_SHAPE}"
    )


def parse_ingredients(raw: str, fallback_text: str) -> list[NutritionResult]:
    """Parse a raw LLM response into a list of ingredient NutritionResults.

    Tolerates a bare array, a ``{"ingredients": [...]}`` wrapper, or a single
    result object. Falls back to one best-effort entry (the raw text, null
    macros) if the response is unparseable or empty.
    """
    fallback = [NutritionResult(fallback_text, None, None, None, None)]
    cleaned = re.sub(r"```json?\s*|\s*```", "", raw or "").strip()
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return fallback

    if isinstance(data, dict):
        if isinstance(data.get("ingredients"), list):
            data = data["ingredients"]
        else:
            data = [data]
    if not isinstance(data, list):
        return fallback

    results: list[NutritionResult] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        description = (item.get("description") or "").strip()
        if not description:
            continue
        results.append(
            NutritionResult(
                description=description,
                calories=item.get("calories"),
                protein=item.get("protein"),
                carbs=item.get("carbs"),
                fat=item.get("fat"),
            )
        )
    return results or fallback


def _last_user_text(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def parse_analysis(
    raw: str, messages: list[dict], allow_questions: bool
) -> AnalysisResult:
    """Parse a raw LLM response into an AnalysisResult.

    Falls back to a best-effort NutritionResult (description only, null macros)
    if the response is unparseable or a question slips through on the final round.
    """
    fallback = NutritionResult(
        description=_last_user_text(messages),
        calories=None,
        protein=None,
        carbs=None,
        fat=None,
    )
    cleaned = re.sub(r"```json?\s*|\s*```", "", raw or "").strip()
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return fallback

    if allow_questions and data.get("type") == "question":
        question = (data.get("question") or "").strip()
        if question:
            return ClarificationNeeded(question=question)
        return fallback

    return NutritionResult(
        description=data.get("description") or fallback.description,
        calories=data.get("calories"),
        protein=data.get("protein"),
        carbs=data.get("carbs"),
        fat=data.get("fat"),
    )


class LLMProvider(ABC):
    @abstractmethod
    async def analyze(
        self, messages: list[dict], allow_questions: bool
    ) -> AnalysisResult:
        """
        Given the conversation so far (a list of {"role", "content"} messages,
        starting with the user's food description), return either structured
        nutrition data or a clarifying question.

        When ``allow_questions`` is False the provider must return a
        NutritionResult (estimating any missing values).
        """
        ...

    @abstractmethod
    async def extract_ingredients(self, text: str) -> list[NutritionResult]:
        """
        Split a single utterance into one or more recipe ingredients, each with
        estimated nutrition. Used by recipe mode so that e.g. "200g pasta and
        20g olive oil" is tracked as two separate ingredients. Never asks
        questions; always estimates.
        """
        ...
