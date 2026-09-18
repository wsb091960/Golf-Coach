from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CoachingAssistantCase(Base):
    __tablename__ = "coaching_assistant_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    goal: Mapped[str] = mapped_column(Text, default="")
    observations_json: Mapped[str] = mapped_column(Text, default="{}")
    preliminary_analysis: Mapped[str] = mapped_column(Text, default="")
    preliminary_plan: Mapped[str] = mapped_column(Text, default="")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    refined_analysis: Mapped[str] = mapped_column(Text, default="")
    refined_plan: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="preliminary")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CoachingAssistantMessage(Base):
    __tablename__ = "coaching_assistant_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("coaching_assistant_cases.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="coach")
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
