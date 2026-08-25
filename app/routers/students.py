from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.store import (
    add_student,
    delete_student,
    get_student,
    list_sessions,
    list_students,
    update_student,
)

APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
router = APIRouter(prefix="/students", tags=["Students"])


def require_student(student_id: str, db: Session) -> dict:
    student = get_student(student_id, db=db)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    return student


@router.get("", response_class=HTMLResponse, name="student_list")
def student_list(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={
            "page_title": "Students",
            "active_page": "students",
            "students": list_students(db=db),
        },
    )


@router.post("", name="student_create")
def student_create(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    skill_level: str = Form(""),
    handedness: str = Form("Unknown"),
    handicap_index: str = Form(""),
    primary_goal: str = Form(""),
    db: Session = Depends(get_db),
):
    handicap_value = None
    if handicap_index.strip():
        try:
            handicap_value = float(handicap_index.strip())
        except ValueError:
            pass

    if handedness not in {"Right", "Left", "Unknown"}:
        handedness = "Unknown"

    student = add_student(
        {
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "email": email.strip(),
            "phone": phone.strip(),
            "skill_level": skill_level.strip(),
            "handedness": handedness,
            "handicap_index": handicap_value,
            "primary_goal": primary_goal.strip(),
            "status": "Active",
        },
        db=db,
    )

    return RedirectResponse(
        url=f"/students/{student['id']}",
        status_code=303,
    )


@router.get("/{student_id}", response_class=HTMLResponse, name="student_profile")
def student_profile(
    request: Request,
    student_id: str,
    db: Session = Depends(get_db),
):
    student = require_student(student_id, db)

    return templates.TemplateResponse(
        request=request,
        name="student_profile.html",
        context={
            "page_title": student.get("name") or "Student Profile",
            "active_page": "students",
            "student": student,
            "student_sessions": list_sessions(
                db=db,
                student_id=student_id,
                limit=100,
            ),
        },
    )


@router.post("/{student_id}/update", name="student_update")
def student_update(
    student_id: str,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    skill_level: str = Form(""),
    handedness: str = Form("Unknown"),
    handicap_index: str = Form(""),
    primary_goal: str = Form(""),
    db: Session = Depends(get_db),
):
    require_student(student_id, db)

    handicap_value = None
    if handicap_index.strip():
        try:
            handicap_value = float(handicap_index.strip())
        except ValueError:
            pass

    if handedness not in {"Right", "Left", "Unknown"}:
        handedness = "Unknown"

    update_student(
        student_id,
        {
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "email": email.strip(),
            "phone": phone.strip(),
            "skill_level": skill_level.strip(),
            "handedness": handedness,
            "handicap_index": handicap_value,
            "primary_goal": primary_goal.strip(),
        },
        db=db,
    )

    return RedirectResponse(
        url=f"/students/{student_id}?saved=1",
        status_code=303,
    )


@router.post("/{student_id}/delete", name="student_delete")
def student_delete(
    student_id: str,
    db: Session = Depends(get_db),
):
    require_student(student_id, db)
    delete_student(student_id, db=db)
    return RedirectResponse(url="/students", status_code=303)
