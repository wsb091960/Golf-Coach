from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.biomechanics import analyze_landmarks
from app.services.biomechanics_x_factor import enrich_with_x_factor
from app.services.biomechanics_shot_evidence import enrich_with_shot_evidence
from app.store import get_session, get_session_shots, update_session
from app.models import CoachingSession, SessionScreenshot, Student
from app.gcie.generated_models import SessionLesson
from app.services.coach_assistant_ai import generate_screenshot_lesson, CoachingAIError
from app.gcie.retrieval import retrieve_approved_knowledge

APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
router = APIRouter(prefix="/biomechanics", tags=["Biomechanics"])

SHOT_FIELDS = (
    "id", "shot_number", "club", "shot_shape", "included", "source",
    "carry_distance", "total_distance", "ball_speed", "club_speed",
    "smash_factor", "launch_angle", "launch_direction", "attack_angle",
    "spin_rate", "spin_axis", "club_path", "club_face", "face_to_path",
    "offline_distance", "apex_height",
)

@router.get("", response_class=HTMLResponse, name="biomechanics")
def biomechanics_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request,name="biomechanics.html",context={"page_title":"Swing & Biomechanics","page_name":"biomechanics"})

@router.get("/session/{session_id}/shots", name="biomechanics_session_shots")
def biomechanics_session_shots(session_id: str, db: Session = Depends(get_db)) -> dict:
    session = get_session(session_id, db=db)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = get_session_shots(session_id, db=db)
    shots = [{key: row.get(key) for key in SHOT_FIELDS} for row in rows if row.get("included", True)]
    return {"shots": shots, "session_notes": session.get("notes") or "", "coaching_notes": session.get("coaching_notes") or ""}



@router.post("/session/{session_id}/coaching-observations", name="save_biomechanics_coaching_observations")
async def save_biomechanics_coaching_observations(session_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    session = get_session(session_id, db=db)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    payload = await request.json()
    plan = str(payload.get("coaching_observations") or "").strip()
    if not plan:
        raise HTTPException(status_code=422, detail="Coaching observations are empty")
    existing = str(session.get("coaching_notes") or "").strip()
    marker = "BIOMECHANICS + GARMIN COACHING PLAN"
    if marker in existing:
        existing = existing.split(marker, 1)[0].rstrip("\n- ")
    combined = (existing + "\n\n" if existing else "") + marker + "\n" + plan
    update_session(session_id, {"coaching_notes": combined}, db=db)
    return {"saved": True, "session_url": f"/sessions/{session_id}"}

@router.post("/analyze", name="analyze_biomechanics")
async def analyze_biomechanics(request: Request) -> dict:
    try:
        payload = await request.json()
        result = analyze_landmarks(payload)
        result = enrich_with_shot_evidence(result, payload.get("shot"))
        return enrich_with_x_factor(result, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/session/{session_id}/lesson", name="generate_biomechanics_lesson")
def generate_biomechanics_lesson(session_id: str, db: Session = Depends(get_db)):
    session = db.get(CoachingSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    student = db.get(Student, session.student_id)
    screenshot_rows = (
        db.query(SessionScreenshot)
        .filter(SessionScreenshot.session_id == session_id)
        .order_by(SessionScreenshot.created_at.desc(), SessionScreenshot.id.desc())
        .limit(10)
        .all()
    )
    screenshot_rows.reverse()
    if not screenshot_rows:
        return RedirectResponse(
            f"/sessions/{session_id}?tab=screenshots&lesson_error=no_screenshots#onform-lesson",
            status_code=303,
        )

    previous_lesson = (
        db.query(SessionLesson)
        .filter(SessionLesson.session_id == session_id)
        .order_by(SessionLesson.created_at.desc())
        .first()
    )
    previously_analyzed_ids = {
        str(value) for value in (previous_lesson.source_screenshot_ids or [])
    } if previous_lesson else set()
    current_screenshot_ids = {str(row.id) for row in screenshot_rows}
    if previous_lesson and not (current_screenshot_ids - previously_analyzed_ids):
        return RedirectResponse(
            f"/sessions/{session_id}?tab=screenshots&lesson_already_exists=1#onform-lesson",
            status_code=303,
        )

    screenshot_inputs = [{
        "filename": row.original_filename,
        "content_type": row.content_type,
        "image_data": row.image_data,
    } for row in screenshot_rows]
    context = "\n".join(part for part in [
        str(session.notes or "").strip(),
        str(session.coaching_notes or "").strip(),
    ] if part)
    goal = "Create one practical, student-readable lesson from the session's Onform screenshots."
    knowledge = retrieve_approved_knowledge(db, goal + " " + context, limit=6)
    try:
        result = generate_screenshot_lesson(
            student_name=(student.name if student else "Student"),
            session_context=context,
            screenshots=screenshot_inputs,
            knowledge_context=knowledge,
        )
    except CoachingAIError:
        return RedirectResponse(
            f"/sessions/{session_id}?tab=screenshots&lesson_error=analysis_failed#onform-lesson",
            status_code=303,
        )

    lesson = SessionLesson(
        session_id=session_id,
        student_notes=result["student_notes"].strip(),
        coach_notes=result["coach_notes"].strip(),
        source_screenshot_ids=[row.id for row in screenshot_rows],
        status="draft",
    )
    db.add(lesson)
    db.commit()
    return RedirectResponse(
        f"/sessions/{session_id}?tab=notes&lesson_created=1",
        status_code=303,
    )
