"""Authenticated, idempotent CRM-to-Golf-Coach student creation."""
import os
import secrets
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.models import Student
from app.store import add_student

router = APIRouter(prefix="/integrations/crm", tags=["CRM integration"])


class CRMStudentLink(Base):
    __tablename__ = "crm_student_links"
    id = Column(Integer, primary_key=True)
    crm_contact_id = Column(Integer, unique=True, nullable=False, index=True)
    student_id = Column(String(64), unique=True, nullable=False)


class IncomingStudent(BaseModel):
    crm_contact_id: int = Field(gt=0)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=50)
    primary_goal: str = Field(default="", max_length=2000)


@router.post("/students")
def create_or_link_student(payload: IncomingStudent,
                           x_golf_sync_key: str | None = Header(default=None),
                           db: Session = Depends(get_db)):
    expected = os.getenv("GOLF_COACH_SYNC_KEY", "").strip()
    if not expected or not x_golf_sync_key or not secrets.compare_digest(expected, x_golf_sync_key):
        raise HTTPException(403, "Integration authentication required")
    existing = db.query(CRMStudentLink).filter_by(crm_contact_id=payload.crm_contact_id).first()
    if existing:
        return {"student_id": existing.student_id, "already_linked": True}
    # Do not merge by name/email: ambiguous matches require manual review.
    student = add_student({"first_name": payload.first_name.strip(),
                           "last_name": payload.last_name.strip(),
                           "email": payload.email.strip(), "phone": payload.phone.strip(),
                           "primary_goal": payload.primary_goal.strip(),
                           "status": "Active"}, db=db)
    db.add(CRMStudentLink(crm_contact_id=payload.crm_contact_id, student_id=str(student["id"])))
    db.commit()
    return {"student_id": str(student["id"]), "already_linked": False}
