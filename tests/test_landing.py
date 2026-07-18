"""Tests for the public landing page at ``/``.

Like the other test modules these call into the app directly rather than through
the HTTP stack (the repo has no test client set up). Config requires an API key at
import time, so dummy env vars are set before importing app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
from fastapi.responses import RedirectResponse

from app.landing.router import landing


class _Request:
    """Stand-in for Request — the landing template needs no request context."""


@pytest.mark.asyncio
async def test_anonymous_visitor_gets_the_landing_page():
    response = await landing(_Request(), user=None)

    assert response.status_code == 200
    body = response.body.decode()
    assert "Jetzt registrieren" in body
    assert 'href="/register"' in body
    assert 'href="/login"' in body
    # Signup is invite-gated, and the page says so rather than leading people
    # into a dead end on /register.
    assert "Invite-Code" in body


@pytest.mark.asyncio
async def test_signed_in_visitor_is_sent_to_the_dashboard():
    response = await landing(_Request(), user=object())

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
