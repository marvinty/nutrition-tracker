from sqlalchemy import text

from app.models.base import Base
from app.models.meal import Meal  # noqa: F401 — must import to register with Base.metadata
from app.models.recipe import Recipe, RecipeIngredient  # noqa: F401 — register with Base.metadata
from app.models.user import User  # noqa: F401 — must import to register with Base.metadata
from app.models.auth_token import AuthToken  # noqa: F401 — must import to register with Base.metadata
from app.models.macro_goal import MacroGoal  # noqa: F401 — must import to register with Base.metadata
from app.models.ai_usage import AiUsage  # noqa: F401 — must import to register with Base.metadata
from app.models.admin_user import AdminUser  # noqa: F401 — must import to register with Base.metadata
from app.models.admin_token import AdminToken  # noqa: F401 — must import to register with Base.metadata
from app.models.signup_code import SignupCode  # noqa: F401 — must import to register with Base.metadata
from app.models.app_setting import AppSetting  # noqa: F401 — must import to register with Base.metadata
from app.models.rate_limit import RateLimitHit  # noqa: F401 — must import to register with Base.metadata
from app.db.session import engine


async def _add_user_tier_column(conn) -> None:
    """Add ``user.tier`` to databases created before tiers existed.

    ``create_all`` only creates missing tables, never missing columns, so an existing
    deployment would otherwise keep a ``user`` table without ``tier`` and fail on every
    login. Idempotent: checks the column list first, so it is a no-op on fresh DBs and
    on every restart after the first.
    """
    columns = await conn.execute(text('PRAGMA table_info("user")'))
    if any(row[1] == "tier" for row in columns):
        return
    await conn.execute(
        text("""ALTER TABLE "user" ADD COLUMN tier TEXT NOT NULL DEFAULT 'free'""")
    )


async def _add_user_email_columns(conn) -> None:
    """Add ``user.email`` and ``user.email_verified_at`` to pre-email databases.

    Two things SQLite forces on us here:

    * ``ALTER TABLE ... ADD COLUMN`` rejects a UNIQUE column, so uniqueness comes from a
      separate index. That is no loss — a unique index still permits many NULLs, which
      is exactly what accounts without an address need.
    * There is no way to add the column and backfill in one statement, hence the
      separate UPDATE below.

    The backfill is the important part. Verification is enforced by comparing
    ``created_at`` against the grace period, so every account that already exists would
    be past its deadline the moment this ships and would find itself locked out of an
    app it was using a minute earlier. Marking them verified grandfathers them in;
    collecting their addresses is a separate, later flow.
    """
    columns = await conn.execute(text('PRAGMA table_info("user")'))
    if any(row[1] == "email" for row in columns):
        return
    await conn.execute(text('ALTER TABLE "user" ADD COLUMN email TEXT'))
    await conn.execute(text('ALTER TABLE "user" ADD COLUMN email_verified_at DATETIME'))
    await conn.execute(
        text('CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email ON "user" (email)')
    )
    await conn.execute(
        text('UPDATE "user" SET email_verified_at = created_at WHERE email IS NULL')
    )


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _add_user_tier_column(conn)
        await _add_user_email_columns(conn)
