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


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _add_user_tier_column(conn)
