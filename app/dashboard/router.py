from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import resolve_user
from app.core.dates_de import (
    format_day_month,
    format_long,
    format_month_year,
    format_short_weekday,
)
from app.core.time import to_local, today_local
from app.db.session import get_session
from app.models.user import User
from app.services.meal_service import (
    get_daily_series,
    get_daily_totals,
    get_period_summary,
    list_meals,
)
from app.services.goal_service import (
    build_progress,
    get_goal,
    period_adherence,
)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.filters["localtime"] = lambda dt: to_local(dt).strftime("%H:%M")
templates.env.filters["de_short"] = format_short_weekday
router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(
    request: Request,
    d: Optional[date] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: Optional[User] = Depends(resolve_user),
):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    today = today_local()
    selected = d or today
    if selected > today:
        selected = today
    is_today = selected == today
    meals = await list_meals(session, user_id=user.username, filter_date=selected)
    totals = await get_daily_totals(session, user_id=user.username, for_date=selected)
    goal = await get_goal(session, user.username)
    progress = build_progress(totals, goal)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "meals": meals,
            "totals": totals,
            "progress": progress,
            "selected": selected.isoformat(),
            "selected_label": format_long(selected),
            "is_today": is_today,
            "prev_date": (selected - timedelta(days=1)).isoformat(),
            "next_date": None if is_today else (selected + timedelta(days=1)).isoformat(),
            "today": today.isoformat(),
            "username": user.username,
        },
    )


@router.get("/recipes")
async def recipes_page(
    request: Request,
    user: Optional[User] = Depends(resolve_user),
):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="recipes.html",
        context={
            "username": user.username,
            "today": today_local().isoformat(),
        },
    )


@router.get("/goals")
async def goals_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: Optional[User] = Depends(resolve_user),
):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    goal = await get_goal(session, user.username)
    return templates.TemplateResponse(
        request=request,
        name="goals.html",
        context={
            "username": user.username,
            "goal": goal,
        },
    )


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _last_of_month(d: date) -> date:
    if d.month == 12:
        return d.replace(day=31)
    return d.replace(month=d.month + 1, day=1) - timedelta(days=1)


def _period_range(view: str, anchor: date) -> tuple[date, date, date, date]:
    """Return (start, end, prev_anchor, next_anchor) for the week/month around anchor."""
    if view == "month":
        start = _first_of_month(anchor)
        end = _last_of_month(anchor)
        prev_anchor = _first_of_month(start - timedelta(days=1))
        next_anchor = end + timedelta(days=1)
    else:  # week (Monday–Sunday)
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
        prev_anchor = start - timedelta(days=7)
        next_anchor = start + timedelta(days=7)
    return start, end, prev_anchor, next_anchor


@router.get("/history")
async def history(
    request: Request,
    view: str = Query(default="week"),
    d: Optional[date] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: Optional[User] = Depends(resolve_user),
):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    if view not in ("week", "month"):
        view = "week"
    today = today_local()
    anchor = d or today
    if anchor > today:
        anchor = today

    start, end, prev_anchor, next_anchor = _period_range(view, anchor)
    series = await get_daily_series(session, user_id=user.username, start=start, end=end)
    summary = get_period_summary(series)
    goal = await get_goal(session, user.username)
    adherence = period_adherence(series, goal)

    if view == "month":
        period_label = format_month_year(start)
    else:
        period_label = f"{format_day_month(start)} – {format_day_month(end, with_year=True)}"

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "view": view,
            "series": series,
            "summary": summary,
            "adherence": adherence,
            "period_label": period_label,
            "prev_anchor": prev_anchor.isoformat(),
            "next_anchor": None if end >= today else next_anchor.isoformat(),
            "today": today.isoformat(),
            "username": user.username,
        },
    )
