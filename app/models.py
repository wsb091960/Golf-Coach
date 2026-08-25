from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), default="")
    last_name: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    skill_level: Mapped[str] = mapped_column(String(100), default="")
    handedness: Mapped[str] = mapped_column(String(20), default="Unknown")
    handicap_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    primary_goal: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    sessions: Mapped[list["CoachingSession"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )

    @property
    def name(self) -> str:
        return " ".join(
            part for part in [self.first_name.strip(), self.last_name.strip()] if part
        )


class CoachingSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
    )
    session_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    session_type: Mapped[str] = mapped_column(String(100), default="Coaching Session")
    primary_club: Mapped[str] = mapped_column(String(100), default="")
    name: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    coaching_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    student: Mapped["Student"] = relationship(back_populates="sessions")
    shots: Mapped[list["Shot"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    videos: Mapped[list["SessionVideo"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )

    @property
    def shot_count(self) -> int:
        return len(self.shots)


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )
    student_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
    )
    shot_number: Mapped[int] = mapped_column(Integer, default=1)
    club: Mapped[str] = mapped_column(String(100), default="", index=True)
    shot_shape: Mapped[str] = mapped_column(String(50), default="")
    source: Mapped[str] = mapped_column(String(50), default="Garmin R10")
    included: Mapped[bool] = mapped_column(default=True)

    ball_speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    club_speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    smash_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    launch_angle: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    launch_direction: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spin_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spin_axis: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carry_distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    apex_height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attack_angle: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    club_path: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    club_face: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    face_to_path: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    offline_distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    raw_signature: Mapped[str] = mapped_column(String(512), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    session: Mapped["CoachingSession"] = relationship(back_populates="shots")


class SessionVideo(Base):
    __tablename__ = "session_videos"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="Onform Video")
    camera_view: Mapped[str] = mapped_column(String(50), default="")
    club: Mapped[str] = mapped_column(String(100), default="")
    shot_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    stored_filename: Mapped[str] = mapped_column(String(255), default="")
    content_type: Mapped[str] = mapped_column(String(100), default="video/mp4")
    source: Mapped[str] = mapped_column(String(50), default="Onform")
    onform_url: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["CoachingSession"] = relationship(back_populates="videos")
