from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.csrf import register_csrf_field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import resolve_user
from app.db.session import get_session
from app.models.user import User
from app.services.signup_code_service import signup_requires_code

# Search landing templates first, plus the dashboard templates for the shared base.html.
_dashboard_templates = Path(__file__).parent.parent / "dashboard" / "templates"
templates = register_csrf_field(
    Jinja2Templates(
        directory=[str(Path(__file__).parent / "templates"), str(_dashboard_templates)]
    )
)
router = APIRouter(tags=["landing"])


@router.get("/", response_class=HTMLResponse)
async def landing(
    request: Request,
    user: Optional[User] = Depends(resolve_user),
    session: AsyncSession = Depends(get_session),
):
    # Inverse of the dashboard guard: signed-in visitors skip the marketing page.
    if user is not None:
        return RedirectResponse(url="/dashboard", status_code=303)
    # Same check the registration form uses, so the CTA never promises a signup
    # the server would reject — or warns about a code that is no longer needed.
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={"needs_code": await signup_requires_code(session)},
    )
