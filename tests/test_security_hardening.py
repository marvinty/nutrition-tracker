"""Tests for the CSRF token check and the sign-in rate limits.

The IP tests matter more than their size suggests: if a caller can choose which key the
limiter counts against, every limit below is decorative. That is the point of reading
X-Forwarded-For from the right.

Config requires an API key at import time, so dummy env vars are set before importing
app modules.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.client_ip import client_ip
from app.core.config import settings
from app.core.csrf import CSRF_FORM_FIELD, _token_from_body, generate_csrf_token
from app.models.base import Base
from app.models.rate_limit import RateLimitHit
from app.services import rate_limit_service as rl


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s


@pytest.fixture(autouse=True)
def limits(monkeypatch):
    monkeypatch.setattr(settings, "login_rate_limit", 3)
    monkeypatch.setattr(settings, "login_rate_window_minutes", 15)
    monkeypatch.setattr(settings, "signup_rate_limit", 2)
    monkeypatch.setattr(settings, "forgot_password_rate_limit", 2)


class _FakeRequest:
    """Enough of a Request for client_ip: headers and a peer address."""

    def __init__(self, headers=None, host="10.0.0.1"):
        self.headers = headers or {}
        self.client = type("C", (), {"host": host})()


# --- client IP ---------------------------------------------------------------


def test_no_proxy_ignores_forwarded_header(monkeypatch):
    """With no proxy in front the header is attacker-controlled, so it is not read."""
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
    request = _FakeRequest({"X-Forwarded-For": "6.6.6.6"}, host="10.0.0.1")
    assert client_ip(request) == "10.0.0.1"


def test_one_proxy_reads_the_rightmost_entry(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    request = _FakeRequest({"X-Forwarded-For": "203.0.113.7"})
    assert client_ip(request) == "203.0.113.7"


def test_forged_prefix_cannot_change_the_identity(monkeypatch):
    """The whole point. A client sending its own X-Forwarded-For has that value
    *prepended* to what the proxy appends, so reading the leftmost entry would let an
    attacker mint a fresh identity per request and never hit a limit."""
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    request = _FakeRequest({"X-Forwarded-For": "6.6.6.6, 203.0.113.7"})
    assert client_ip(request) == "203.0.113.7"


def test_two_proxies_count_two_from_the_right(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
    request = _FakeRequest({"X-Forwarded-For": "6.6.6.6, 203.0.113.7, 172.16.0.1"})
    assert client_ip(request) == "203.0.113.7"


def test_too_few_entries_falls_back_to_the_peer(monkeypatch):
    """A header shorter than the configured chain means the request did not arrive the
    expected way; the socket address is the only trustworthy thing left."""
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
    request = _FakeRequest({"X-Forwarded-For": "203.0.113.7"}, host="10.0.0.1")
    assert client_ip(request) == "10.0.0.1"


def test_missing_header_falls_back_to_the_peer(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert client_ip(_FakeRequest(host="10.0.0.1")) == "10.0.0.1"


# --- rate limiting -----------------------------------------------------------


@pytest.mark.asyncio
async def test_under_the_limit_passes(session):
    key = rl.ip_key("1.1.1.1")
    for _ in range(2):
        await rl.record_hit(session, rl.LOGIN, key)
    await rl.enforce(session, rl.LOGIN, key)  # 2 < 3, no raise


@pytest.mark.asyncio
async def test_at_the_limit_raises_429(session):
    key = rl.ip_key("1.1.1.1")
    for _ in range(3):
        await rl.record_hit(session, rl.LOGIN, key)
    with pytest.raises(Exception) as exc:
        await rl.enforce(session, rl.LOGIN, key)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


@pytest.mark.asyncio
async def test_keys_are_independent(session):
    for _ in range(3):
        await rl.record_hit(session, rl.LOGIN, rl.ip_key("1.1.1.1"))
    await rl.enforce(session, rl.LOGIN, rl.ip_key("2.2.2.2"))


@pytest.mark.asyncio
async def test_scopes_are_independent(session):
    """Burning the login budget must not lock someone out of registering."""
    for _ in range(3):
        await rl.record_hit(session, rl.LOGIN, rl.ip_key("1.1.1.1"))
    await rl.enforce(session, rl.SIGNUP, rl.ip_key("1.1.1.1"))


@pytest.mark.asyncio
async def test_account_and_ip_namespaces_cannot_collide(session):
    """An account literally named like an IP must not share that IP's bucket."""
    for _ in range(3):
        await rl.record_hit(session, rl.LOGIN, rl.account_key("1.1.1.1"))
    await rl.enforce(session, rl.LOGIN, rl.ip_key("1.1.1.1"))


@pytest.mark.asyncio
async def test_account_key_is_case_insensitive(session):
    for _ in range(3):
        await rl.record_hit(session, rl.LOGIN, rl.account_key("Marvin@Example.DE"))
    with pytest.raises(Exception) as exc:
        await rl.enforce(session, rl.LOGIN, rl.account_key(" marvin@example.de "))
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_either_key_alone_can_trip_the_limit(session):
    """enforce takes both keys because each covers a case the other misses."""
    ip, account = rl.ip_key("1.1.1.1"), rl.account_key("a@b.de")
    for _ in range(3):
        await rl.record_hit(session, rl.LOGIN, account)
    with pytest.raises(Exception):
        await rl.enforce(session, rl.LOGIN, ip, account)


@pytest.mark.asyncio
async def test_old_hits_fall_out_of_the_window(session):
    """A sliding window, not a fixed one: attempts age out individually."""
    key = rl.ip_key("1.1.1.1")
    stale = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=20)
    for _ in range(5):
        session.add(RateLimitHit(scope=rl.LOGIN, key=key, created_at=stale))
    await session.commit()
    assert await rl.count_hits(session, rl.LOGIN, key) == 0
    await rl.enforce(session, rl.LOGIN, key)


@pytest.mark.asyncio
async def test_clear_hits_resets_one_key_only(session):
    ip, account = rl.ip_key("1.1.1.1"), rl.account_key("a@b.de")
    await rl.record_failure(session, rl.LOGIN, ip, account)
    await rl.clear_hits(session, rl.LOGIN, account)
    assert await rl.count_hits(session, rl.LOGIN, account) == 0
    # The IP keeps its budget: on a shared address one success must not wipe the
    # failures an attacker on the same network is accumulating.
    assert await rl.count_hits(session, rl.LOGIN, ip) == 1


@pytest.mark.asyncio
async def test_prune_drops_only_expired_rows(session):
    key = rl.ip_key("1.1.1.1")
    stale = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=20)
    session.add(RateLimitHit(scope=rl.LOGIN, key=key, created_at=stale))
    await session.commit()
    await rl.record_hit(session, rl.LOGIN, key)

    assert await rl.prune_expired(session) == 1
    assert await rl.count_hits(session, rl.LOGIN, key) == 1


@pytest.mark.asyncio
async def test_none_keys_are_skipped(session):
    await rl.enforce(session, rl.LOGIN, None)
    await rl.record_failure(session, rl.LOGIN, None)


@pytest.mark.asyncio
async def test_signup_scope_uses_its_own_smaller_limit(session):
    key = rl.ip_key("1.1.1.1")
    for _ in range(2):
        await rl.record_hit(session, rl.SIGNUP, key)
    with pytest.raises(Exception) as exc:
        await rl.enforce(session, rl.SIGNUP, key)
    assert exc.value.status_code == 429


# --- CSRF --------------------------------------------------------------------


def test_token_is_read_from_a_urlencoded_body():
    body = f"{CSRF_FORM_FIELD}=abc123&email=a%40b.de".encode()
    assert (
        _token_from_body(body, "application/x-www-form-urlencoded") == "abc123"
    )


def test_token_survives_other_fields_around_it():
    body = f"email=a%40b.de&{CSRF_FORM_FIELD}=abc123&password=x".encode()
    assert _token_from_body(body, "application/x-www-form-urlencoded") == "abc123"


def test_missing_token_reads_as_empty():
    assert _token_from_body(b"email=a%40b.de", "application/x-www-form-urlencoded") == ""


def test_multipart_bodies_are_not_parsed():
    """Multipart is the audio upload, which is called from JS and sends the header
    instead — buffering a whole recording to find a text field would be wasteful."""
    body = f"{CSRF_FORM_FIELD}=abc123".encode()
    assert _token_from_body(body, "multipart/form-data; boundary=x") == ""


def test_tokens_are_unique_and_long():
    tokens = {generate_csrf_token() for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(t) >= 32 for t in tokens)
