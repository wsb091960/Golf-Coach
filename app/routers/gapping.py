from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.store import get_student_shots, list_sessions, list_students

APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
router = APIRouter(prefix="/gapping", tags=["Gapping"])

SHOT_FIELDS = ("id","session_id","shot_number","club","included","source","carry_distance","total_distance","offline_distance","ball_speed","club_speed","smash_factor","launch_angle","spin_rate","apex_height","shot_shape")

@router.get("", response_class=HTMLResponse, name="gapping_page")
def gapping_page(request: Request, student_id: str = "", session_id: str = "", db: Session = Depends(get_db)):
    students = list_students(db=db)
    selected_student = student_id or (str(students[0].get("id")) if students else "")
    sessions = list_sessions(db=db, student_id=selected_student) if selected_student else []
    shots = get_student_shots(selected_student, db=db) if selected_student else []
    if session_id:
        shots = [shot for shot in shots if str(shot.get("session_id")) == session_id]
    clean = [{key: shot.get(key) for key in SHOT_FIELDS} for shot in shots if shot.get("included", True) and shot.get("club")]
    return templates.TemplateResponse(request=request,name="gapping.html",context={"page_title":"Club Gapping","page_name":"gapping","students":students,"sessions":sessions,"selected_student_id":selected_student,"selected_session_id":session_id,"gapping_shots":clean})
