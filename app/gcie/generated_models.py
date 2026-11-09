"""Standalone generated GCIE lesson plans; no student/session data changes."""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Text, DateTime
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
