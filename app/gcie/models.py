"""GCIE case records: additive tables, separate from existing session workflows."""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

def new_id():
    return str(uuid4())

class CoachingCase(Base):
    __tablename__ = "gcie_coaching_cases"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    coach_id: Mapped[str] = mapped_column(String(128), default="owner", index=True)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    problem: Mapped[str] = mapped_column(Text, default="")
    observations: Mapped[dict] = mapped_column(JSON, default=dict)
    measurements_before: Mapped[dict] = mapped_column(JSON, default=dict)
    hypotheses: Mapped[list] = mapped_column(JSON, default=list)
    intervention: Mapped[dict] = mapped_column(JSON, default=dict)
    measurements_after: Mapped[dict] = mapped_column(JSON, default=dict)
    outcome: Mapped[str] = mapped_column(Text, default="")
    evidence_quality: Mapped[str] = mapped_column(String(24), default="unrated")
    source_refs: Mapped[list] = mapped_column(JSON, default=list)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
