"""Legt einen Testnutzer fuer die lokale Entwicklung an.

Warum ein Skript und keine Umgebungsvariable: der Admin wird beim Start aus
ADMIN_USERNAME/ADMIN_PASSWORD angelegt (services/admin_service.ensure_bootstrap_admin),
weil man sich sonst nach einem verlorenen Passwort aus dem eigenen Adminbereich
aussperrt. Fuer einen normalen Nutzer gibt es diesen Grund nicht. Derselbe
Mechanismus fuer einen Nutzer hiesse: eine Codebahn, die bei jedem Start ein Konto
mit einem Passwort aus der Umgebung anlegt — auf dem Proxmox-Host genauso wie hier.
Eine falsch gesetzte Variable in der Produktionsumgebung waere dann ein echtes Konto
mit einem Testpasswort. Der Nutzen ist lokal, also bleibt der Code lokal.

Aufruf im laufenden Container:

    docker exec -w /app -e PYTHONPATH=/app nutrition-tracker-api-1 \
        python scripts/seed_test_user.py

PYTHONPATH muss sein: das Image startet uvicorn mit app.main als Modul, ein direkt
aufgerufenes Skript unter scripts/ findet das Paket sonst nicht.

Optional: Benutzername, E-Mail und Passwort als Argumente. Laeuft mehrfach; ein
bereits vorhandenes Konto wird nicht angelegt, sondern nur gemeldet.
"""

import asyncio
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.user import User
from app.services.auth_service import create_user

DEFAULT_USERNAME = "test"
DEFAULT_EMAIL = "test@example.invalid"
DEFAULT_PASSWORD = "testtest12"  # PASSWORD_MIN_LENGTH ist 10


def _is_local() -> bool:
    base = (settings.public_base_url or "").lower()
    return "localhost" in base or "127.0.0.1" in base or base == ""


async def main() -> int:
    args = sys.argv[1:]
    if "--force" in args:
        args.remove("--force")
        forced = True
    else:
        forced = False

    if not _is_local() and not forced:
        print(
            f"PUBLIC_BASE_URL ist {settings.public_base_url!r} — das sieht nicht nach\n"
            "einer lokalen Installation aus. Kein Testkonto angelegt. Wenn das doch\n"
            "gewollt ist: nochmal mit --force.",
            file=sys.stderr,
        )
        return 1

    username = args[0] if len(args) > 0 else DEFAULT_USERNAME
    email = args[1] if len(args) > 1 else DEFAULT_EMAIL
    password = args[2] if len(args) > 2 else DEFAULT_PASSWORD

    async with async_session_maker() as session:
        existing = await session.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none() is not None:
            print(f"Nutzer {username!r} existiert bereits — nichts geaendert.")
            return 0

        user = await create_user(
            session, username=username, email=email, password=password
        )
        # Sofort bestaetigt: sonst sperrt die Karenzzeit das Konto nach
        # EMAIL_VERIFY_GRACE_MINUTES aus, und die Bestaetigungsmail landet lokal
        # nur im Log.
        user.email_verified_at = datetime.now(timezone.utc)
        await session.commit()

    print(f"Angelegt: {username} / {email} / {password}")
    print("Anmeldung laeuft ueber die E-Mail-Adresse, nicht den Benutzernamen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
