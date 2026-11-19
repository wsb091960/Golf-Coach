"""Manual, non-persistent swing geometry teaching model."""
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
router = APIRouter(tags=["Swing Geometry Lab"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/swing-geometry-lab", response_class=HTMLResponse, name="swing_geometry_lab")
def swing_geometry_lab(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="swing_geometry_lab.html",
        context={"page_title": "Swing Geometry Lab", "page_name": "swing-geometry-lab"},
    )
