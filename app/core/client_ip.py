"""Determining the real client IP behind a reverse proxy.

This is load-bearing for rate limiting: if a caller can choose the IP the limiter
counts against, the limiter does nothing. It deserves its own module and its own
tests.
"""

from typing import Optional
from fastapi import Request
from app.core.config import settings


def client_ip(request: Request) -> str:
    """The caller's IP, counted from the right of ``X-Forwarded-For``.

    ``settings.trusted_proxy_hops`` is how many proxies of our own sit in front of the
    app. Each appends the address it received the request from, so with one proxy the
    header reads ``<client>`` and with two ``<client>, <proxy1>``. Anything a client
    sends itself is *prepended* to that — a request arriving with a forged
    ``X-Forwarded-For: 1.2.3.4`` reaches the app as ``1.2.3.4, <real client>``.

    So the trustworthy entry is the Nth from the *right*, never the first. Reading the
    leftmost value is the classic mistake here, and it hands an attacker a fresh
    identity per request simply by varying a header — which would make every limit in
    this app decorative.

    With ``trusted_proxy_hops = 0`` the header is ignored entirely, because without a
    proxy to overwrite it there is nothing about it that can be trusted.
    """
    hops = settings.trusted_proxy_hops
    if hops > 0:
        forwarded = request.headers.get("X-Forwarded-For", "")
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(parts) >= hops:
            return parts[-hops]
        # Fewer entries than configured hops means the request did not come through
        # the expected chain. Fall back to the peer address rather than trusting a
        # header that is now the wrong shape.

    return _peer_ip(request)


def _peer_ip(request: Request) -> str:
    """The address of whoever opened the socket. Unspoofable, but it is the proxy's
    address when one is in front — hence the header handling above."""
    client: Optional[object] = request.client
    return getattr(client, "host", None) or "unknown"
