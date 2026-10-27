from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

router = APIRouter(tags=["Public Website"])


@router.get("/", response_class=HTMLResponse, name="public_home")
def public_home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="public_home.html",
        context={"page_title": "WSBCO Golf | Reedsport Golf Course"},
    )
