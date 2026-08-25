"""
=========================================================
WSBCO Golf Coach
Pydantic Schemas

File: app/schemas.py
Version: 1.0.0
=========================================================
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# Student
# -----------------------------

class StudentBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    handedness: str = "Right"
    handicap_index: Optional[float] = None
    skill_level: Optional[str] = None
    goals: Optional[str] = None
    notes: Optional[str] = None
    active: bool = True


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    handicap_index: Optional[float] = None
    skill_level: Optional[str] = None
    goals: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class StudentRead(StudentBase, ORMBase):
    id: int
    created_at: datetime
    updated_at: datetime


# -----------------------------
# Golf Session
# -----------------------------

class SessionBase(BaseModel):
    student_id: int
    session_date: date
    session_type: str = "Practice"
    location: Optional[str] = None
    coach_name: Optional[str] = None
    primary_club: Optional[str] = None
    focus_area: Optional[str] = None
    coach_notes: Optional[str] = None
    player_feedback: Optional[str] = None
    completed: bool = False


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    session_type: Optional[str] = None
    location: Optional[str] = None
    coach_name: Optional[str] = None
    primary_club: Optional[str] = None
    focus_area: Optional[str] = None
    coach_notes: Optional[str] = None
    player_feedback: Optional[str] = None
    completed: Optional[bool] = None


class SessionRead(SessionBase, ORMBase):
    id: int
    created_at: datetime
    updated_at: datetime


# -----------------------------
# Shot
# -----------------------------

class ShotBase(BaseModel):
    session_id: int
    shot_number: int
    club: Optional[str] = None
    shot_shape: Optional[str] = None
    carry_distance: Optional[float] = None
    total_distance: Optional[float] = None
    ball_speed: Optional[float] = None
    club_speed: Optional[float] = None
    smash_factor: Optional[float] = None
    launch_angle: Optional[float] = None
    spin_rate: Optional[float] = None
    club_path: Optional[float] = None
    club_face: Optional[float] = None
    face_to_path: Optional[float] = None
    attack_angle: Optional[float] = None
    notes: Optional[str] = None


class ShotCreate(ShotBase):
    pass

class ShotUpdate(BaseModel):
    club: Optional[str] = None
    shot_shape: Optional[str] = None
    carry_distance: Optional[float] = None
    total_distance: Optional[float] = None
    ball_speed: Optional[float] = None
    club_speed: Optional[float] = None
    smash_factor: Optional[float] = None
    launch_angle: Optional[float] = None
    spin_rate: Optional[float] = None
    club_path: Optional[float] = None
    club_face: Optional[float] = None
    face_to_path: Optional[float] = None
    attack_angle: Optional[float] = None
    notes: Optional[str] = None

class ShotRead(ShotBase, ORMBase):
    id: int
    created_at: datetime
    updated_at: datetime


# -----------------------------
# Garmin Import
# -----------------------------

class GarminImportRead(ORMBase):
    id: int
    session_id: int
    original_filename: str
    import_status: str
    rows_detected: int
    rows_imported: int
    rows_skipped: int
    imported_at: Optional[datetime] = None


# -----------------------------
# Health
# -----------------------------

class HealthResponse(BaseModel):
    status: str
    application: str
    version: str
    environment: str
