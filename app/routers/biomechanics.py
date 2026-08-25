from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.biomechanics import analyze_landmarks
from app.services.biomechanics_x_factor import enrich_with_x_factor
from app.services.biomechanics_shot_evidence import enrich_with_shot_evidence
from app.store import get_session, get_session_shots, update_session

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
