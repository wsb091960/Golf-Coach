"""Owner-authenticated GCIE JSON endpoints. No LLM-generated case is auto-approved."""
from datetime import datetime
from urllib.parse import quote_plus
from pathlib import Path
from fastapi.responses import PlainTextResponse, HTMLResponse, RedirectResponse
from fastapi import Form, Request
from fastapi.templating import Jinja2Templates
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CoachingSession
from app.gcie.models import CoachingCase, KnowledgeEntry, KnowledgeSource
from app.gcie.retrieval import retrieve_approved_knowledge

router = APIRouter(prefix="/gcie", tags=["GCIE"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / 'templates'))
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
    if not case.problem.strip() or not case.intervention or not case.outcome.strip() or case.outcome == "not_tested":
        raise HTTPException(422, "A documented, tested outcome is required for approval")
    case.status = "approved"
    case.reviewed_by = "owner"
    case.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(case)
    return serialize(case)


def serialize_source(source):
    return {key: getattr(source, key) for key in (
        "id", "title", "source_type", "citation", "source_url", "summary",
        "evidence_quality", "status", "review_notes", "coach_id",
        "reviewed_by", "reviewed_at", "created_at", "updated_at"
    )}


def serialize_entry(entry):
    return {key: getattr(entry, key) for key in (
        "id", "source_id", "title", "category", "teaching_level",
        "knowledge_text", "tags", "evidence_quality", "status", "version",
        "coach_id", "reviewed_by", "reviewed_at", "created_at", "updated_at"
    )}


@router.get("/knowledge", response_class=HTMLResponse)
def knowledge_page(request: Request, q: str = "", db: Session = Depends(get_db)):
    sources = db.scalars(select(KnowledgeSource).order_by(KnowledgeSource.created_at.desc()).limit(100)).all()
    entries = db.scalars(select(KnowledgeEntry).order_by(KnowledgeEntry.updated_at.desc()).limit(100)).all()
    approved_sources = [source for source in sources if source.status == "approved"]
    results = retrieve_approved_knowledge(db, q, limit=20) if q.strip() else []
    return templates.TemplateResponse(request=request, name="gcie_knowledge.html", context={
        "page_title": "GCIE Knowledge Base", "active_page": "gcie-knowledge",
        "sources": sources, "entries": entries, "approved_sources": approved_sources,
        "search_results": results, "q": q.strip(),
    })


@router.post("/knowledge/sources")
def add_knowledge_source(
    title: str = Form(...), source_type: str = Form(...), citation: str = Form(""),
    source_url: str = Form(""), summary: str = Form(""),
    evidence_quality: str = Form("unrated"), db: Session = Depends(get_db)
):
    title, citation, source_url, summary = title.strip(), citation.strip(), source_url.strip(), summary.strip()
    if not title or len(title) > 255 or len(citation) > 2000 or len(source_url) > 2000 or len(summary) > 5000:
        raise HTTPException(422, "Check source title, citation, link, and summary lengths.")
    if source_type not in {"pga_framework", "coach_preference", "tgm", "tpi", "p_positions", "ball_flight", "coach_case_pattern", "other"}:
        raise HTTPException(422, "Choose a valid source type.")
    if evidence_quality not in {"unrated", "coach_observation", "reference", "research"}:
        raise HTTPException(422, "Choose a valid evidence label.")
    source = KnowledgeSource(title=title, source_type=source_type, citation=citation,
                             source_url=source_url, summary=summary,
                             evidence_quality=evidence_quality, status="candidate")
    db.add(source)
    db.commit()
    return RedirectResponse("/gcie/knowledge?message=Source+saved+for+review", status_code=303)


@router.post("/knowledge/sources/{source_id}/review")
def review_knowledge_source(
    source_id: str, decision: str = Form(...), review_notes: str = Form(""),
    db: Session = Depends(get_db)
):
    source = db.get(KnowledgeSource, source_id)
    if source is None:
        raise HTTPException(404, "Knowledge source not found")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(422, "Choose approved or rejected.")
    source.status = decision
    source.review_notes = review_notes.strip()[:5000]
    source.reviewed_by = "owner"
    source.reviewed_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/gcie/knowledge?message=Source+review+saved", status_code=303)


@router.post("/knowledge/entries")
def add_knowledge_entry(
    source_id: str = Form(...), title: str = Form(...), category: str = Form(...),
    teaching_level: str = Form(...), knowledge_text: str = Form(...),
    evidence_quality: str = Form("unrated"), tags: str = Form(""),
    db: Session = Depends(get_db)
):
    source = db.get(KnowledgeSource, source_id)
    if source is None:
        raise HTTPException(422, "Select a saved source record.")
    title, knowledge_text = title.strip(), knowledge_text.strip()
    if not title or len(title) > 255 or not knowledge_text or len(knowledge_text) > 8000:
        raise HTTPException(422, "Entry needs a title and text (maximum 8,000 characters).")
    categories = {"PGA framework", "Teaching preference", "Six Laws", "Fourteen Principles",
                  "Nine Ball Flights", "TGM", "TPI", "P-Positions", "Biomechanics",
                  "Drill", "Coach case pattern", "Other"}
    levels = {"governing", "preference", "supporting"}
    qualities = {"unrated", "coach_observation", "reference", "research"}
    if category not in categories or teaching_level not in levels or evidence_quality not in qualities:
        raise HTTPException(422, "Choose valid category, teaching level, and evidence label.")
    clean_tags = list(dict.fromkeys(tag.strip()[:60] for tag in tags.split(",") if tag.strip()))[:20]
    entry = KnowledgeEntry(source_id=source.id, title=title, category=category,
                           teaching_level=teaching_level, knowledge_text=knowledge_text,
                           tags=clean_tags, evidence_quality=evidence_quality, status="draft")
    db.add(entry)
    db.commit()
    return RedirectResponse("/gcie/knowledge?message=Knowledge+entry+saved+as+draft", status_code=303)


@router.post("/knowledge/entries/{entry_id}/approve")
def approve_knowledge_entry(entry_id: str, db: Session = Depends(get_db)):
    entry = db.get(KnowledgeEntry, entry_id)
    if entry is None:
        raise HTTPException(404, "Knowledge entry not found")
    source = db.get(KnowledgeSource, entry.source_id)
    if source is None or source.status != "approved":
        raise HTTPException(409, "Approve the source record before approving this knowledge entry.")
    if not entry.title.strip() or not entry.knowledge_text.strip():
        raise HTTPException(422, "A title and knowledge text are required.")
    entry.status = "approved"
    entry.reviewed_by = "owner"
    entry.reviewed_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/gcie/knowledge?message=Knowledge+entry+approved+for+retrieval", status_code=303)


@router.get("/knowledge/retrieve")
def retrieve_knowledge(q: str, limit: int = 6, db: Session = Depends(get_db)):
    if len(q.strip()) < 2:
        raise HTTPException(422, "Search term must be at least two characters.")
    return retrieve_approved_knowledge(db, q, limit=max(1, min(limit, 20)))


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

@router.get("/sessions/{session_id}/lesson-plan", response_class=HTMLResponse)
def lesson_plan_page(request: Request, session_id: str, db: Session = Depends(get_db)):
    session = db.get(CoachingSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    from app.models import Student
    student = db.get(Student, session.student_id)
    plan = (Path(__file__).resolve().parent / "lesson_plans" / "001_straight_pull_to_pull_fade.md").read_text(encoding="utf-8")
    cases = db.scalars(select(CoachingCase).where(CoachingCase.session_id == session_id).order_by(CoachingCase.created_at.desc())).all()
    return templates.TemplateResponse(request=request, name="gcie_lesson_plan.html", context={
        "student": student, "session": session, "plan": plan, "cases": cases,
        "saved": request.query_params.get("saved") == "1"
    })

@router.post("/sessions/{session_id}/lesson-plan/outcome")
def record_lesson_outcome(session_id: str, problem: str = Form("Straight pull to controlled pull fade"),
                          outcome_status: str = Form(...), coach_notes: str = Form(""),
                          club_path_before: str = Form(""), club_path_after: str = Form(""),
                          club_face_before: str = Form(""), club_face_after: str = Form(""),
                          face_to_path_before: str = Form(""), face_to_path_after: str = Form(""),
                          launch_direction_before: str = Form(""), launch_direction_after: str = Form(""),
                          offline_distance_before: str = Form(""), offline_distance_after: str = Form(""),
                          db: Session = Depends(get_db)):
    session = db.get(CoachingSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if outcome_status not in {"not_tested", "achieved", "partial", "no_improvement"}:
        raise HTTPException(422, "Invalid outcome status")
    keys = ("club_path", "club_face", "face_to_path", "launch_direction", "offline_distance")
    before, after = {}, {}
    values = locals()
    for key in keys:
        for suffix, target in (("before", before), ("after", after)):
            raw = values[f"{key}_{suffix}"].strip()
            if raw:
                try:
                    target[key] = float(raw)
                except ValueError:
                    raise HTTPException(422, f"Invalid numeric value: {key} {suffix}")
    case = CoachingCase(
        student_id=session.student_id, session_id=session.id,
        problem=problem.strip() or "Straight pull to controlled pull fade",
        observations={"coach_notes": coach_notes, "goal": "controlled pull fade",
                      "lesson_plan": "001_straight_pull_to_pull_fade.md"},
        measurements_before=before, measurements_after=after,
        intervention={"reference_plan": "001_straight_pull_to_pull_fade.md"},
        outcome=outcome_status, evidence_quality="unrated",
        source_refs=["gcie/lesson_plans/001_straight_pull_to_pull_fade.md"]
    )
    db.add(case)
    db.commit()
    return RedirectResponse(f"/gcie/sessions/{session_id}/lesson-plan?saved=1", status_code=303)


@router.get("/lesson-plans", response_class=HTMLResponse)
def lesson_plan_library(request: Request, db: Session = Depends(get_db)):
    """Permanent lesson plan library, available without selecting a student."""
    return templates.TemplateResponse(request=request, name="gcie_lesson_library.html", context={
        "page_title": "Lesson Plans", "active_page": "lesson-plans",
        "generated_plans": db.scalars(select(GeneratedLessonPlan).order_by(GeneratedLessonPlan.created_at.desc()).limit(100)).all()
    })

# Standalone pattern lesson generator. Does not modify student/session workflows.
from app.gcie.generated_models import GeneratedLessonPlan
from app.gcie.lesson_generator import PATTERNS, generate

@router.post("/lesson-plans/generate")
def generate_lesson_plan(pattern: str = Form(...), handedness: str = Form(...),
                         club: str = Form(...), observations: str = Form(""),
                         db: Session = Depends(get_db)):
    if pattern not in PATTERNS or handedness not in {"right", "left"} or club not in {"Driver", "Fairway wood", "Hybrid", "Iron", "Wedge"}:
        raise HTTPException(422, "Invalid lesson plan selection")
    if len(observations) > 4000:
        raise HTTPException(422, "Observations too long")
    title = f"{club} — {pattern.replace('-', ' ').title()} ({handedness.title()}-handed)"
    record = GeneratedLessonPlan(title=title, pattern=pattern, handedness=handedness,
                                 club=club, observations=observations,
                                 plan_text=generate(pattern, handedness, club, observations))
    db.add(record)
    db.commit()
    return RedirectResponse(f"/gcie/lesson-plans/generated/{record.id}", status_code=303)

@router.get("/lesson-plans/generated/{plan_id}", response_class=HTMLResponse)
def generated_lesson_plan(request: Request, plan_id: str, db: Session = Depends(get_db)):
    record = db.get(GeneratedLessonPlan, plan_id)
    if record is None:
        raise HTTPException(404, "Lesson plan not found")
    return templates.TemplateResponse(request=request, name="gcie_generated_lesson.html",
                                      context={"plan": record, "active_page": "lesson-plans",
                                               "video_links": [(name, "https://www.youtube.com/results?search_query=" + quote_plus(name + " golf " + record.pattern.replace("-", " ") + " " + record.club)) for name in ("Clay Ballard", "Eric Cogorno")]})
