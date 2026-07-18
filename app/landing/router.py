from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.deps import resolve_user
from app.models.user import User

# Search landing templates first, plus the dashboard templates for the shared base.html.
_dashboard_templates = Path(__file__).parent.parent / "dashboard" / "templates"
templates = Jinja2Templates(
    directory=[str(Path(__file__).parent / "templates"), str(_dashboard_templates)]
)
router = APIRouter(tags=["landing"])


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request, user: Optional[User] = Depends(resolve_user)):
    # Inverse of the dashboard guard: signed-in visitors skip the marketing page.
    if user is not None:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="landing.html", context={})
