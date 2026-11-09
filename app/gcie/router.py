"""Owner-authenticated GCIE JSON endpoints. No LLM-generated case is auto-approved."""
from datetime import datetime
from pathlib import Path
from fastapi.responses import PlainTextResponse
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CoachingSession
from app.gcie.models import CoachingCase

router = APIRouter(prefix="/gcie", tags=["GCIE"])
FIELDS = ("problem", "observations", "measurements_before", "hypotheses",
          "intervention", "measurements_after", "outcome", "evidence_quality", "source_refs")

class CaseInput(BaseModel):
    student_id: str
    session_id: str
    problem: str = ""
    observations: dict = Field(default_factory=dict)
    measurements_before: dict = Field(default_factory=dict)
    hypotheses: list = Field(default_factory=list)
    intervention: dict = Field(default_factory=dict)
    measurements_after: dict = Field(default_factory=dict)
    outcome: str = ""
    evidence_quality: str = "unrated"
    source_refs: list = Field(default_factory=list)

def serialize(case):
    return {key: getattr(case, key) for key in (
        "id", "student_id", "session_id", "coach_id", "status", *FIELDS,
        "reviewed_by", "reviewed_at", "created_at", "updated_at")}

def require_case(db, case_id):
    case = db.get(CoachingCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case

@router.post("/cases")
def create_case(payload: CaseInput, db: Session = Depends(get_db)):
    session = db.get(CoachingSession, payload.session_id)
    if not session or session.student_id != payload.student_id:
        raise HTTPException(422, "Session must belong to student")
    case = CoachingCase(student_id=payload.student_id, session_id=payload.session_id,
                        **{key: getattr(payload, key) for key in FIELDS})
    db.add(case)
    db.commit()
    db.refresh(case)
    return serialize(case)

@router.get("/cases")
def list_cases(student_id: str | None = None, session_id: str | None = None,
               approved_only: bool = False, db: Session = Depends(get_db)):
    stmt = select(CoachingCase)
    if student_id:
        stmt = stmt.where(CoachingCase.student_id == student_id)
    if session_id:
        stmt = stmt.where(CoachingCase.session_id == session_id)
    if approved_only:
        stmt = stmt.where(CoachingCase.status == "approved")
    return [serialize(c) for c in db.scalars(stmt.order_by(CoachingCase.created_at.desc())).all()]

@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    return serialize(require_case(db, case_id))

@router.put("/cases/{case_id}")
def edit_case(case_id: str, payload: CaseInput, db: Session = Depends(get_db)):
    case = require_case(db, case_id)
    if case.status == "approved":
        raise HTTPException(409, "Approved cases are immutable; create a new case for revisions")
    if case.student_id != payload.student_id or case.session_id != payload.session_id:
        raise HTTPException(422, "Cannot change case ownership or session")
    for key in FIELDS:
        setattr(case, key, getattr(payload, key))
    case.status = "draft"
    db.commit()
    db.refresh(case)
    return serialize(case)

@router.post("/cases/{case_id}/approve")
def approve_case(case_id: str, db: Session = Depends(get_db)):
    case = require_case(db, case_id)
    if not case.problem.strip() or not case.intervention or not case.outcome.strip():
        raise HTTPException(422, "Problem, intervention, and outcome required for approval")
    case.status = "approved"
    case.reviewed_by = "owner"
    case.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(case)
    return serialize(case)

@router.get("/knowledge/search")
def search_knowledge(q: str, limit: int = 20, db: Session = Depends(get_db)):
    """Initial keyword retrieval; embeddings and ranking are a later milestone."""
    q = q.strip()
    if len(q) < 2:
        raise HTTPException(422, "Search term must be at least two characters")
    limit = max(1, min(limit, 50))
    matches = db.scalars(
        select(CoachingCase).where(
            CoachingCase.status == "approved",
            or_(CoachingCase.problem.ilike(f"%{q}%"),
                CoachingCase.outcome.ilike(f"%{q}%"))
        ).limit(limit)
    ).all()
    return [serialize(c) for c in matches]


@router.get("/lesson-plans/straight-pull-to-pull-fade", response_class=PlainTextResponse)
def straight_pull_to_pull_fade_plan():
    """Read-only permanent reference lesson plan, separate from approved case evidence."""
    plan = Path(__file__).resolve().parent / "lesson_plans" / "001_straight_pull_to_pull_fade.md"
    return PlainTextResponse(plan.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")
