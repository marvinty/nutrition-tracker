import re
import secrets
import bcrypt

# Deliberately loose: anything with a local part, an "@" and a dotted domain. The only
# check that really proves an address works is whether the confirmation mail arrives,
# so a stricter regex would just reject valid exotic addresses for no gain.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


class InvalidEmailError(ValueError):
    """Raised when an address is not shaped like an email address."""


def normalize_email(email: str) -> str:
    """Lower-case and strip ``email``, or raise ``InvalidEmailError``.

    Every read and write of an address goes through here. Storing one form and looking
    up another would let "Foo@x.de" register a second account alongside "foo@x.de"
    without ever tripping the unique constraint.
    """
    normalized = email.strip().lower()
    if not _EMAIL_RE.match(normalized):
        raise InvalidEmailError(email)
    return normalized


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(32)
