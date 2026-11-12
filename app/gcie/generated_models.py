"""Standalone generated GCIE lesson plans; no student/session data changes."""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class GeneratedLessonPlan(Base):
    __tablename__ = "gcie_generated_lesson_plans"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(200))
    pattern: Mapped[str] = mapped_column(String(40))
    handedness: Mapped[str] = mapped_column(String(10))
    club: Mapped[str] = mapped_column(String(40))
    observations: Mapped[str] = mapped_column(Text, default="")
    plan_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SessionLesson(Base):
    """Paired coach and student notes generated from one session review."""
    __tablename__ = "gcie_session_lessons"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_notes: Mapped[str] = mapped_column(Text, nullable=False)
    coach_notes: Mapped[str] = mapped_column(Text, nullable=False)
    source_screenshot_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
