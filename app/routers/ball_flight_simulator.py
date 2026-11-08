from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.store import get_session_shots, get_student, list_sessions

APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
router = APIRouter(tags=["Ball Flight Simulator"])


@router.get("/ball-flight-simulator", response_class=HTMLResponse, name="ball_flight_simulator")
def ball_flight_simulator(request: Request, db: Session = Depends(get_db)):
    sessions = []
    for session in list_sessions(db=db, limit=100):
        student = get_student(str(session.get("student_id") or ""), db=db)
        sessions.append(
            {
                **session,
                "student_name": student.get("name") if student else "Unknown Student",
                "shots": get_session_shots(str(session["id"]), db=db),
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="ball_flight_simulator.html",
        context={
            "page_title": "Ball Flight Simulator",
            "sessions": sessions,
        },
    )
