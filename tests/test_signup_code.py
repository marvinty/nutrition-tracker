"""Tests for the invite-code gate on registration.

Closing signup is what stops someone creating accounts in bulk to farm free credits;
the credit limits in test_usage only cap the damage per account. Config requires an
API key at import time, so we set dummy env vars before importing app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest

from app.core.config import settings
from app.services.auth_service import signup_code_ok


@pytest.fixture
def code(monkeypatch):
    monkeypatch.setattr(settings, "signup_code", "kraftsport2026")


def test_open_signup_when_no_code_configured(monkeypatch):
    monkeypatch.setattr(settings, "signup_code", "")
    assert signup_code_ok("") is True
    assert signup_code_ok("anything") is True


def test_correct_code_is_accepted(code):
    assert signup_code_ok("kraftsport2026") is True


def test_surrounding_whitespace_is_tolerated(code):
    # People paste the code out of a chat message; leading/trailing space is not a typo.
    assert signup_code_ok("  kraftsport2026 ") is True


@pytest.mark.parametrize("attempt", ["", "   ", "wrong", "kraftsport", "Kraftsport2026"])
def test_wrong_or_missing_code_is_rejected(code, attempt):
    # Case matters — "Kraftsport2026" must not pass.
    assert signup_code_ok(attempt) is False
