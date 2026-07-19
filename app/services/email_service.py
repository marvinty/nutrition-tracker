"""Outgoing transactional mail.

One provider (Resend) and one fallback (the log). There is no sender abstraction on
purpose: a Protocol with swappable backends buys nothing while there is exactly one
real backend, and the log fallback already covers the case it would be built for.
"""

import logging
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

_RESEND_ENDPOINT = "https://api.resend.com/emails"
_TIMEOUT = 10.0


def build_url(path: str) -> str:
    """Absolute link into the app for use inside an email."""
    return f"{settings.public_base_url.rstrip('/')}/{path.lstrip('/')}"


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send one mail. Returns whether it went out; never raises.

    Callers sit in the middle of registration and password-reset flows, where the mail
    is a side effect and not the point. A provider outage must not turn a successful
    signup into an error page — the user is already registered, and both flows offer a
    re-send. So delivery failures are logged and swallowed.
    """
    if not settings.resend_api_key:
        # Dev and test path: no key configured, so the message (and crucially the link
        # inside it) goes to the log where it can be clicked out of `make logs`.
        logger.warning(
            "E-Mail nicht versandt (RESEND_API_KEY fehlt). An: %s | Betreff: %s\n%s",
            to,
            subject,
            html,
        )
        return False

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                _RESEND_ENDPOINT,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.email_from,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
        if response.status_code >= 400:
            logger.error(
                "Resend lehnte die Mail an %s ab: %s %s",
                to,
                response.status_code,
                response.text,
            )
            return False
        # Logged on success too, so that an empty log means "never attempted" rather
        # than being indistinguishable from "sent fine".
        logger.info("Mail an %s verschickt: %s", to, subject)
        return True
    except httpx.HTTPError:
        logger.exception("Mailversand an %s fehlgeschlagen", to)
        return False


async def send_verification_email(to: str, username: str, token: str) -> bool:
    from app.services.email_templates import verification_email

    subject, html = verification_email(username, build_url(f"/verify-email?token={token}"))
    return await send_email(to, subject, html)


async def send_password_reset_email(to: str, username: str, token: str) -> bool:
    from app.services.email_templates import password_reset_email

    subject, html = password_reset_email(
        username, build_url(f"/reset-password?token={token}")
    )
    return await send_email(to, subject, html)


def sender_configured() -> Optional[str]:
    """The configured sender address, or None when mail only goes to the log."""
    return settings.email_from if settings.resend_api_key else None
