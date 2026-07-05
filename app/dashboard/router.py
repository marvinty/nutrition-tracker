from datetime import date
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import resolve_user
from app.db.session import get_session
from app.models.user import User
from app.services.meal_service import get_daily_totals, list_meals

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: Optional[User] = Depends(resolve_user),
):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    today = date.today()
    meals = await list_meals(session, user_id=user.username, filter_date=today)
    totals = await get_daily_totals(session, user_id=user.username, for_date=today)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "meals": meals,
            "totals": totals,
            "today": today.strftime("%A, %B %d %Y"),
            "username": user.username,
        },
    )
