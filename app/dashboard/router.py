from datetime import date
from pathlib import Path
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.services.meal_service import get_daily_totals, list_meals

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    today = date.today()
    meals = await list_meals(session, user_id=user_id, filter_date=today)
    totals = await get_daily_totals(session, user_id=user_id, for_date=today)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "meals": meals,
            "totals": totals,
            "today": today.strftime("%A, %B %d %Y"),
            "user_id": user_id,
        },
    )
