"""Standalone, manual-input D-plane teaching lab within Golf Coach."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["D-Plane Lab"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/d-plane-lab", response_class=HTMLResponse, name="d_plane_lab")
def d_plane_lab(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="d_plane_lab.html",
        context={"page_title": "D-Plane Lab", "page_name": "d-plane-lab"},
    )
