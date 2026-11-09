"""GCIE isolated database tests. No production data or network calls."""
import os
import tempfile
from pathlib import Path

temp = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(temp.name) / "gcie-test.db")
from app.database import Base, engine, SessionLocal
from app.models import Student, CoachingSession
from app.gcie.models import CoachingCase
from app.gcie.router import CaseInput, create_case, edit_case, approve_case, search_knowledge, record_lesson_outcome
from fastapi import HTTPException
import pytest

@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        session.add(Student(id="test-student", first_name="Test", last_name="Golfer"))
        session.add(CoachingSession(id="test-session", student_id="test-student"))
        session.commit()
        yield session
        session.rollback()
    Base.metadata.drop_all(engine)

def test_case_lifecycle(db):
    payload = CaseInput(student_id="test-student", session_id="test-session",
        problem="Straight pull", intervention={"drill": "Start-line gate"}, outcome="partial")
    case = create_case(payload, db)
    assert case["status"] == "draft"
    assert search_knowledge("pull", db=db) == []
    approved = approve_case(case["id"], db)
    assert approved["status"] == "approved"
    assert len(search_knowledge("pull", db=db)) == 1
    with pytest.raises(HTTPException) as error:
        edit_case(case["id"], payload, db)
    assert error.value.status_code == 409

def test_invalid_student_session_pair(db):
    with pytest.raises(HTTPException) as error:
        create_case(CaseInput(student_id="other", session_id="test-session"), db)
    assert error.value.status_code == 422

def test_untested_cannot_be_approved(db):
    case = create_case(CaseInput(student_id="test-student", session_id="test-session",
        problem="Pull fade", intervention={"reference_plan": "001"}, outcome="not_tested"), db)
    with pytest.raises(HTTPException) as error:
        approve_case(case["id"], db)
    assert error.value.status_code == 422

def test_lesson_outcome_creates_draft(db):
    response = record_lesson_outcome(session_id="test-session",
        problem="Straight pull to controlled pull fade", outcome_status="partial",
        coach_notes="Start line improved", club_path_before="-1", club_path_after="-3",
        club_face_before="", club_face_after="", face_to_path_before="",
        face_to_path_after="", launch_direction_before="", launch_direction_after="",
        offline_distance_before="", offline_distance_after="", db=db)
    assert response.status_code == 303
    case = db.query(CoachingCase).one()
    assert case.status == "draft"
    assert case.measurements_before["club_path"] == -1.0
    assert case.measurements_after["club_path"] == -3.0

def test_reference_plan_exists():
    path = Path(__file__).resolve().parents[1] / "app/gcie/lesson_plans/001_straight_pull_to_pull_fade.md"
    assert "P1" in path.read_text()
    assert "Garmin R10" in path.read_text()
