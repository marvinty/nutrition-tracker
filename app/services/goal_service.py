from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.macro_goal import MacroGoal
from app.schemas.goal import GoalUpdate

MACROS = ("calories", "protein", "carbs", "fat")


async def get_goal(session: AsyncSession, user_id: str) -> Optional[MacroGoal]:
    result = await session.execute(
        select(MacroGoal).where(MacroGoal.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_goal(
    session: AsyncSession, user_id: str, data: GoalUpdate
) -> MacroGoal:
    """Create or fully replace a user's macro targets.

    PUT semantics: every macro is set to the provided value, so passing ``None``
    for a field clears that target ("kein Ziel").
    """
    goal = await get_goal(session, user_id)
    fields = data.model_dump()
    if goal is None:
        goal = MacroGoal(user_id=user_id, **fields)
        session.add(goal)
    else:
        for field, value in fields.items():
            setattr(goal, field, value)
    await session.commit()
    await session.refresh(goal)
    return goal


def build_progress(totals: dict, goal: Optional[MacroGoal]) -> dict:
    """Per-macro progress vs. target, only for macros with a positive target.

    Pure function (no DB). Macros without a target are omitted, so the template
    renders those cards unchanged. Returns a dict keyed by macro name with
    ``current``, ``target``, ``percent`` (real, for display), ``bar_pct``
    (0–100 clamped, for bar width), ``remaining`` and ``over``.
    """
    if goal is None:
        return {}
    progress: dict = {}
    for macro in MACROS:
        target = getattr(goal, macro, None)
        if not target:  # None or 0 → no goal for this macro
            continue
        current = totals.get(macro, 0) or 0
        percent = round(current / target * 100)
        progress[macro] = {
            "current": round(current, 1),
            "target": round(target, 1),
            "percent": percent,
            "bar_pct": min(100, max(0, percent)),
            "remaining": round(target - current, 1),
            "over": current > target,
        }
    return progress


def period_adherence(series: list[dict], goal: Optional[MacroGoal]) -> Optional[dict]:
    """Count logged days that hit the protein target over a daily series.

    Protein is the Kraftsport lead metric. Only days with at least one meal
    count. Returns ``None`` when no protein target is set.
    """
    if goal is None or not goal.protein:
        return None
    target = goal.protein
    logged_days = 0
    protein_hit = 0
    for entry in series:
        if entry.get("meal_count", 0) <= 0:
            continue
        logged_days += 1
        if (entry.get("protein") or 0) >= target:
            protein_hit += 1
    return {
        "protein_hit": protein_hit,
        "logged_days": logged_days,
        "protein_target": round(target, 1),
    }
