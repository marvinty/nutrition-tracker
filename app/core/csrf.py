"""CSRF protection via the double-submit cookie pattern.

A random token is handed out in a cookie and must come back in the request — as a
hidden form field, or as an ``X-CSRF-Token`` header for the dashboard's fetch calls.
An attacker's page can *cause* a cross-site request but cannot read our cookie to
learn what value to echo, so the two only match when the request came from our own
pages.

Worth being clear about what this adds, since the app is not starting from zero: the
session cookie is already ``SameSite=Lax``, which means browsers do not attach it to
cross-site POSTs at all. That is the primary defence and it was already in place. This
covers what Lax does not — an attacker who controls a sibling subdomain (same site,
different origin), and browsers old enough to ignore SameSite. Defence in depth, not a
hole being plugged.

Requests authenticated by ``Authorization: Bearer`` are exempt: a cross-origin page
cannot set that header without our consent via CORS, so those carry no CSRF risk, and
requiring a token would break every non-browser API client.
"""

import secrets
from urllib.parse import parse_qs
from fastapi import Request
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context
from markupsafe import Markup, escape
from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse, Response
from app.core.config import settings

CSRF_COOKIE_NAME = "csrftoken"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_FORM_FIELD = "csrf_token"

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _token_from_body(body: bytes, content_type: str) -> str:
    """Pull the hidden field out of a form body.

    Only urlencoded bodies are parsed here. Multipart is left alone deliberately: the
    audio upload is the one multipart endpoint and it is called from JavaScript, which
    sends the header instead — parsing a file upload in middleware just to find a text
    field would mean buffering the whole recording twice.
    """
    if not content_type.startswith("application/x-www-form-urlencoded"):
        return ""
    parsed = parse_qs(body.decode("utf-8", errors="replace"))
    values = parsed.get(CSRF_FORM_FIELD)
    return values[0].strip() if values else ""


class CSRFMiddleware:
    """Validate the token on unsafe methods, and issue one on the way out.

    Written as raw ASGI rather than on ``BaseHTTPMiddleware`` because checking a form
    field means reading the request body, and under BaseHTTPMiddleware that consumes
    the stream the route handler is about to read — every form POST would arrive at its
    handler empty. Here the body is buffered and replayed through a fresh ``receive``,
    so the handler sees exactly what the client sent.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope, receive)
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)

        if request.method not in _SAFE_METHODS and not _is_bearer_auth(request):
            submitted = request.headers.get(CSRF_HEADER_NAME, "").strip()
            if not submitted:
                body = await _read_body(receive)
                receive = _replay(body)
                submitted = _token_from_body(
                    body, request.headers.get("content-type", "")
                )
            # compare_digest, not ==, so a timing difference cannot be used to recover
            # the token a character at a time.
            if (
                not cookie_token
                or not submitted
                or not secrets.compare_digest(cookie_token, submitted)
            ):
                # A Response is itself an ASGI app, so it can be called directly here.
                return await _rejected(request)(scope, receive, send)

        # Templates read this to render the hidden field. Set before the handler runs,
        # so a first-time visitor's form already carries the token that the cookie
        # below establishes.
        issued = cookie_token or generate_csrf_token()
        scope.setdefault("state", {})["csrf_token"] = issued

        if cookie_token:
            return await self.app(scope, receive, send)
        await self.app(scope, receive, _with_cookie(send, issued))


async def _read_body(receive) -> bytes:
    body = b""
    while True:
        message = await receive()
        if message["type"] != "http.request":
            break
        body += message.get("body", b"")
        if not message.get("more_body", False):
            break
    return body


def _replay(body: bytes):
    """A ``receive`` that hands the buffered body to the next consumer."""
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _with_cookie(send, token: str):
    """Wrap ``send`` to attach the CSRF cookie to the response headers."""

    async def wrapped(message):
        if message["type"] == "http.response.start":
            cookie = Response()
            cookie.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=token,
                # Deliberately readable by JavaScript, unlike the session cookie: the
                # dashboard's fetch calls need it to build the header. Safe, because
                # the token authenticates nothing on its own — it only proves the
                # request came from a page on our own origin.
                httponly=False,
                samesite="lax",
                secure=settings.cookie_secure,
                max_age=settings.session_ttl_days * 24 * 60 * 60,
            )
            headers = MutableHeaders(scope=message)
            headers.append("set-cookie", cookie.headers["set-cookie"])
        await send(message)

    return wrapped


@pass_context
def csrf_field(context) -> Markup:
    """``{{ csrf_field() }}`` — the hidden input every form needs.

    A template global rather than something threaded through each route's context
    dict, so adding a form cannot silently forget to pass the token along.
    """
    request = context.get("request")
    token = getattr(request.state, "csrf_token", "") if request is not None else ""
    return Markup(
        f'<input type="hidden" name="{CSRF_FORM_FIELD}" value="{escape(token)}">'
    )


def register_csrf_field(templates: Jinja2Templates) -> Jinja2Templates:
    """Make ``csrf_field`` available to one template environment."""
    templates.env.globals["csrf_field"] = csrf_field
    return templates


def _is_bearer_auth(request: Request) -> bool:
    return request.headers.get("Authorization", "").startswith("Bearer ")


def _rejected(request: Request) -> Response:
    detail = "Sicherheitsprüfung fehlgeschlagen. Bitte lade die Seite neu."
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=403, content={"detail": detail})
    # A plain response rather than a rendered template: reaching this from a real
    # browser almost always means a stale tab, and reloading is the whole fix.
    return Response(
        content=(
            f"<!doctype html><meta charset='utf-8'><title>Abgelaufen</title>"
            f"<p style='font-family:sans-serif;max-width:34em;margin:15vh auto;"
            f"line-height:1.6'>{detail}</p>"
        ),
        status_code=403,
        media_type="text/html",
    )
