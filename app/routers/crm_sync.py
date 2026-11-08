from __future__ import annotations

import os
import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CRMStudentLink, Student

router = APIRouter(prefix="/integrations/crm", tags=["CRM Integration"])


class CRMStudentPayload(BaseModel):
    crm_contact_id: int = Field(gt=0)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(default="", max_length=100)
    email: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=50)
    primary_goal: str = Field(default="", max_length=4000)

    @field_validator("first_name", "last_name", "email", "phone", "primary_goal", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


def _authorize_sync(value: str | None) -> None:
    expected = os.getenv("GOLF_CRM_SYNC_KEY", "").strip()
    if not expected or not value or not secrets.compare_digest(value, expected):
        raise HTTPException(status_code=403, detail="CRM sync authentication required")


@router.post("/students", name="crm_create_student")
def create_student_from_crm(
    payload: CRMStudentPayload,
    x_golf_sync_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _authorize_sync(x_golf_sync_key)
    linked = db.get(CRMStudentLink, payload.crm_contact_id)
    if linked:
        return {
            "crm_contact_id": payload.crm_contact_id,
            "student_id": linked.student_id,
            "already_linked": True,
        }

    normalized_email = payload.email.strip().lower()
    if normalized_email:
        existing = db.scalar(
            select(Student).where(
                func.lower(Student.email) == normalized_email,
                Student.email != "",
            ).limit(1)
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail="A Golf Coach student already uses this email. Review the existing student before converting.",
            )

    student = Student(
        id=str(uuid4()),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=normalized_email,
        phone=payload.phone.strip(),
        skill_level="New Golfer",
        handedness="Unknown",
        primary_goal=payload.primary_goal.strip(),
        status="Active",
    )
    db.add(student)
    db.flush()
    db.add(
        CRMStudentLink(
            crm_contact_id=payload.crm_contact_id,
            student_id=student.id,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        linked = db.get(CRMStudentLink, payload.crm_contact_id)
        if linked:
            return {
                "crm_contact_id": payload.crm_contact_id,
                "student_id": linked.student_id,
                "already_linked": True,
            }
        raise HTTPException(status_code=409, detail="Student conversion conflicted with another request.")

    return {
        "crm_contact_id": payload.crm_contact_id,
        "student_id": student.id,
        "already_linked": False,
    }
