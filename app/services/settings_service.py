"""Runtime settings an admin can change from the panel, backed by ``AppSetting``.

Kept tiny on purpose: one typed accessor pair per setting, so callers never deal with
the string encoding or with a missing row.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.app_setting import AppSetting

SIGNUP_CLOSED = "signup_closed"


async def _get(session: AsyncSession, key: str) -> Optional[str]:
    result = await session.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting is not None else None


async def _set(session: AsyncSession, key: str, value: str) -> None:
    result = await session.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        session.add(AppSetting(key=key, value=value))
    else:
        setting.value = value
    await session.commit()


async def is_signup_closed(session: AsyncSession) -> bool:
    """Whether registration requires an invite code. Defaults to open, matching the
    behaviour before the panel existed."""
    return await _get(session, SIGNUP_CLOSED) == "1"


async def set_signup_closed(session: AsyncSession, closed: bool) -> None:
    await _set(session, SIGNUP_CLOSED, "1" if closed else "0")
