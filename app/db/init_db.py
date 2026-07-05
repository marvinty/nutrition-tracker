from app.models.base import Base
from app.models.meal import Meal  # noqa: F401 — must import to register with Base.metadata
from app.models.user import User  # noqa: F401 — must import to register with Base.metadata
from app.models.auth_token import AuthToken  # noqa: F401 — must import to register with Base.metadata
from app.db.session import engine


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
