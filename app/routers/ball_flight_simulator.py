from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
router = APIRouter(tags=["Ball Flight Simulator"])


@router.get("/ball-flight-simulator", response_class=HTMLResponse, name="ball_flight_simulator")
def ball_flight_simulator(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="ball_flight_simulator.html",
        context={"page_title": "Ball Flight Simulator"},
    )
