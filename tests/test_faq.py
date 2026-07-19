"""Tests for the public FAQ page at ``/faq``.

Same direct-call style as test_landing.py. Unlike most of the suite these actually
render a template that extends ``base.html``, so they double as the only guard
against a Jinja syntax error or a broken block in the shared layout.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest

from app.core.config import settings
from app.landing.router import faq


class _State:
    csrf_token = "test-token"
    user = None


class _Request:
    """Stand-in for Request. base.html reads request.state for the verify banner
    and the CSRF token, so the stub carries a state object."""

    state = _State()


class _User:
    username = "marvin"


@pytest.mark.asyncio
async def test_anonymous_visitor_gets_the_faq():
    response = await faq(_Request(), user=None)

    assert response.status_code == 200
    body = response.body.decode()
    # The signed-out nav variant: auth entry points, no logout form.
    assert 'href="/login"' in body
    assert 'href="/register"' in body
    assert 'action="/logout"' not in body


@pytest.mark.asyncio
async def test_signed_in_visitor_gets_the_app_nav():
    body = (await faq(_Request(), user=_User())).body.decode()

    assert "marvin" in body
    assert 'action="/logout"' in body
    assert 'href="/faq"' in body


@pytest.mark.asyncio
async def test_credit_numbers_come_from_the_settings():
    """The whole point of passing these through: the page cannot drift from the
    real budgets when the config changes."""
    body = (await faq(_Request(), user=None)).body.decode()

    assert f"{settings.tier_daily_credits['free']} Credits pro Tag" in body
    assert f"{settings.tier_daily_credits['pro']} Credits pro Tag" in body
    assert f"{settings.credit_costs['voice']}&nbsp;Credits" in body
    assert settings.app_timezone in body
