"""HTML bodies for outgoing mail.

Inline styles only and no external stylesheet: mail clients strip <style> blocks and
never fetch remote CSS. Kept deliberately plain — a text-heavy mail with one link lands
in the inbox far more reliably than a rich layout.
"""

import html as _html

_WRAPPER = (
    "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
    'font-size:16px;line-height:1.6;color:#1a1a1a;max-width:520px;margin:0 auto;'
    'padding:24px">{body}'
    '<p style="margin-top:32px;font-size:13px;color:#888">Nutrition Tracker</p></div>'
)

_BUTTON = (
    '<p style="margin:28px 0"><a href="{url}" '
    'style="background:#1a1a1a;color:#fff;text-decoration:none;padding:12px 20px;'
    'border-radius:8px;display:inline-block">{label}</a></p>'
    # Repeated as plain text because some clients suppress the styled anchor, and a
    # confirmation mail whose link cannot be reached is a dead end for the account.
    '<p style="font-size:13px;color:#666">Falls der Button nicht funktioniert, '
    'kopiere diesen Link in deinen Browser:<br>'
    '<span style="word-break:break-all">{url}</span></p>'
)


def verification_email(username: str, url: str) -> tuple[str, str]:
    body = (
        f"<p>Hallo {_html.escape(username)},</p>"
        "<p>bitte bestätige deine E-Mail-Adresse, damit dein Konto dauerhaft "
        "nutzbar bleibt.</p>"
        + _BUTTON.format(url=_html.escape(url, quote=True), label="E-Mail bestätigen")
        + "<p>Der Link ist 24 Stunden gültig. Wenn du dich nicht registriert hast, "
        "kannst du diese Mail ignorieren.</p>"
    )
    return "Bestätige deine E-Mail-Adresse", _WRAPPER.format(body=body)


def password_reset_email(username: str, url: str) -> tuple[str, str]:
    body = (
        f"<p>Hallo {_html.escape(username)},</p>"
        "<p>du hast ein neues Passwort angefordert.</p>"
        + _BUTTON.format(url=_html.escape(url, quote=True), label="Neues Passwort setzen")
        + "<p>Der Link ist eine Stunde gültig. Wenn du das nicht warst, musst du "
        "nichts tun — dein aktuelles Passwort bleibt gültig.</p>"
    )
    return "Passwort zurücksetzen", _WRAPPER.format(body=body)
