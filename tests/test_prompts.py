"""Tests for the system prompts.

The prompts are written in English, which without an explicit rule makes the
model answer in English too — a user logging "zwei Spiegeleier" got back
"2 Fried Eggs". These guard the instruction that fixes it, in all three prompt
variants.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest

from app.providers.base import build_ingredients_prompt, build_system_prompt


@pytest.mark.parametrize(
    "prompt",
    [
        build_system_prompt(allow_questions=True),
        build_system_prompt(allow_questions=False),
        build_ingredients_prompt(),
    ],
    ids=["analyze-with-questions", "analyze-final", "ingredients"],
)
def test_prompt_pins_the_response_language(prompt):
    assert "LANGUAGE:" in prompt
    assert "GERMAN" in prompt


def test_language_rule_covers_the_question_text_too():
    """The clarifying question is shown verbatim in a German UI, so the rule has
    to name it explicitly and not just the description."""
    prompt = build_system_prompt(allow_questions=True)
    rule = prompt[prompt.index("LANGUAGE:") :]
    assert "question" in rule
    assert "description" in rule
