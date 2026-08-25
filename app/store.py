"""
WSBCO Golf Coach
Persistent SQLAlchemy-backed store.

This replaces the former in-memory store while preserving
the same public helper names used by the routers.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import SessionLocal
from app.models import CoachingSession, Shot, Student

Record = dict[str, Any]


def generate_id() -> str:
    return str(uuid4())


def _get_db(db: Session | None) -> tuple[Session, bool]:
    if db is not None:
        return db, False
    return SessionLocal(), True


def _close_if_needed(db: Session, should_close: bool) -> None:
    if should_close:
        db.close()


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return date.today()
    try:
        return datetime.fromisoformat(
            text.replace("Z", "+00:00")
        ).date()
    except ValueError:
        return date.today()


def _student_dict(student: Student) -> Record:
    return {
        "id": student.id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "name": student.name,
        "email": student.email,
        "phone": student.phone,
        "skill_level": student.skill_level,
        "handedness": student.handedness,
        "handicap_index": student.handicap_index,
        "primary_goal": student.primary_goal,
        "status": student.status,
        "created_at": student.created_at.isoformat() if student.created_at else "",
        "updated_at": student.updated_at.isoformat() if student.updated_at else "",
    }


def _session_dict(session: CoachingSession) -> Record:
    return {
        "id": session.id,
        "student_id": session.student_id,
        "session_date": session.session_date.isoformat() if session.session_date else "",
        "session_type": session.session_type,
        "primary_club": session.primary_club,
        "name": session.name,
        "notes": session.notes,
        "coaching_notes": session.coaching_notes,
        "shot_count": len(session.shots) if session.shots is not None else 0,
        "created_at": session.created_at.isoformat() if session.created_at else "",
        "updated_at": session.updated_at.isoformat() if session.updated_at else "",
    }


def _shot_dict(shot: Shot) -> Record:
    return {
        "id": shot.id,
        "session_id": shot.session_id,
        "student_id": shot.student_id,
        "shot_number": shot.shot_number,
        "club": shot.club,
        "shot_shape": shot.shot_shape,
        "source": shot.source,
        "included": shot.included,
        "ball_speed": shot.ball_speed,
        "club_speed": shot.club_speed,
        "smash_factor": shot.smash_factor,
        "launch_angle": shot.launch_angle,
        "launch_direction": shot.launch_direction,
        "spin_rate": shot.spin_rate,
        "spin_axis": shot.spin_axis,
        "carry_distance": shot.carry_distance,
        "total_distance": shot.total_distance,
        "apex_height": shot.apex_height,
        "attack_angle": shot.attack_angle,
        "club_path": shot.club_path,
        "club_face": shot.club_face,
        "face_angle": shot.club_face,
        "face_to_path": shot.face_to_path,
        "offline_distance": shot.offline_distance,
        "raw_signature": shot.raw_signature,
        "created_at": shot.created_at.isoformat() if shot.created_at else "",
        "updated_at": shot.updated_at.isoformat() if shot.updated_at else "",
    }


# ==========================================================
# STUDENTS
# ==========================================================

def list_students(
    *,
    db: Session | None = None,
    limit: int | None = None,
) -> list[Record]:
    db, close = _get_db(db)
    try:
        stmt = select(Student).order_by(
            Student.updated_at.desc()
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return [
            _student_dict(row)
            for row in db.scalars(stmt).all()
        ]
    finally:
        _close_if_needed(db, close)


def get_student(
    student_id: str,
    *,
    db: Session | None = None,
) -> Record | None:
    db, close = _get_db(db)
    try:
        row = db.get(Student, str(student_id))
        return _student_dict(row) if row else None
    finally:
        _close_if_needed(db, close)


def add_student(
    student: Record,
    *,
    db: Session | None = None,
) -> Record:
    db, close = _get_db(db)
    try:
        row = Student(
            id=str(student.get("id") or generate_id()),
            first_name=str(student.get("first_name") or "").strip(),
            last_name=str(student.get("last_name") or "").strip(),
            email=str(student.get("email") or "").strip(),
            phone=str(student.get("phone") or "").strip(),
            skill_level=str(student.get("skill_level") or "").strip(),
            handedness=str(student.get("handedness") or "Unknown").strip(),
            handicap_index=student.get("handicap_index"),
            primary_goal=str(student.get("primary_goal") or "").strip(),
            status=str(student.get("status") or "Active"),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _student_dict(row)
    finally:
        _close_if_needed(db, close)


def create_student(
    name: str = "",
    *,
    db: Session | None = None,
    **fields: Any,
) -> Record:
    first_name = str(fields.pop("first_name", "") or "")
    last_name = str(fields.pop("last_name", "") or "")

    if name and not (first_name or last_name):
        parts = name.strip().split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

    return add_student(
        {
            "first_name": first_name,
            "last_name": last_name,
            **fields,
        },
        db=db,
    )


def update_student(
    student_id: str,
    updates: Record,
    *,
    db: Session | None = None,
) -> Record | None:
    db, close = _get_db(db)
    try:
        row = db.get(Student, str(student_id))
        if row is None:
            return None

        allowed = {
            "first_name",
            "last_name",
            "email",
            "phone",
            "skill_level",
            "handedness",
            "handicap_index",
            "primary_goal",
            "status",
        }

        for key, value in updates.items():
            if key in allowed:
                setattr(row, key, value)

        row.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(row)
        return _student_dict(row)
    finally:
        _close_if_needed(db, close)


def delete_student(
    student_id: str,
    *,
    db: Session | None = None,
) -> bool:
    db, close = _get_db(db)
    try:
        row = db.get(Student, str(student_id))
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True
    finally:
        _close_if_needed(db, close)


# ==========================================================
# SESSIONS
# ==========================================================

def list_sessions(
    *,
    db: Session | None = None,
    limit: int | None = None,
    student_id: str | None = None,
) -> list[Record]:
    db, close = _get_db(db)
    try:
        stmt = (
            select(CoachingSession)
            .options(selectinload(CoachingSession.shots))
            .order_by(
                CoachingSession.session_date.desc(),
                CoachingSession.created_at.desc(),
            )
        )

        if student_id:
            stmt = stmt.where(
                CoachingSession.student_id == str(student_id)
            )

        if limit is not None:
            stmt = stmt.limit(limit)

        return [
            _session_dict(row)
            for row in db.scalars(stmt).all()
        ]
    finally:
        _close_if_needed(db, close)


def get_session(
    session_id: str,
    *,
    db: Session | None = None,
) -> Record | None:
    db, close = _get_db(db)
    try:
        stmt = (
            select(CoachingSession)
            .options(selectinload(CoachingSession.shots))
            .where(CoachingSession.id == str(session_id))
        )
        row = db.scalar(stmt)
        return _session_dict(row) if row else None
    finally:
        _close_if_needed(db, close)


def add_session(
    session: Record,
    *,
    db: Session | None = None,
) -> Record:
    db, close = _get_db(db)
    try:
        row = CoachingSession(
            id=str(session.get("id") or generate_id()),
            student_id=str(session.get("student_id") or "").strip(),
            session_date=_parse_date(session.get("session_date")),
            session_type=str(
                session.get("session_type")
                or "Coaching Session"
            ).strip(),
            primary_club=str(session.get("primary_club") or "").strip(),
            name=str(session.get("name") or "").strip(),
            notes=str(session.get("notes") or "").strip(),
            coaching_notes=str(session.get("coaching_notes") or "").strip(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        return {
            **_session_dict(row),
            "shot_count": 0,
        }
    finally:
        _close_if_needed(db, close)


def create_session(
    student_id: str = "",
    name: str = "",
    *,
    db: Session | None = None,
    **fields: Any,
) -> Record:
    return add_session(
        {
            "student_id": str(student_id).strip(),
            "name": str(name).strip(),
            **fields,
        },
        db=db,
    )


def update_session(
    session_id: str,
    updates: Record,
    *,
    db: Session | None = None,
) -> Record | None:
    db, close = _get_db(db)
    try:
        stmt = (
            select(CoachingSession)
            .options(selectinload(CoachingSession.shots))
            .where(CoachingSession.id == str(session_id))
        )
        row = db.scalar(stmt)

        if row is None:
            return None

        allowed = {
            "session_type",
            "primary_club",
            "name",
            "notes",
            "coaching_notes",
        }

        for key, value in updates.items():
            if key in allowed:
                setattr(row, key, value)

        if "session_date" in updates:
            row.session_date = _parse_date(
                updates["session_date"]
            )

        row.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(row)

        return _session_dict(row)
    finally:
        _close_if_needed(db, close)


def delete_session(
    session_id: str,
    *,
    db: Session | None = None,
) -> bool:
    db, close = _get_db(db)
    try:
        row = db.get(CoachingSession, str(session_id))
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True
    finally:
        _close_if_needed(db, close)


# ==========================================================
# SHOTS
# ==========================================================

def list_shots(
    *,
    db: Session | None = None,
    limit: int | None = None,
    session_id: str | None = None,
    student_id: str | None = None,
    included_only: bool = False,
) -> list[Record]:
    db, close = _get_db(db)
    try:
        stmt = select(Shot).order_by(
            Shot.session_id.asc(),
            Shot.shot_number.asc(),
        )

        if session_id:
            stmt = stmt.where(
                Shot.session_id == str(session_id)
            )

        if student_id:
            stmt = stmt.where(
                Shot.student_id == str(student_id)
            )

        if included_only:
            stmt = stmt.where(
                Shot.included.is_(True)
            )

        if limit is not None:
            stmt = stmt.limit(limit)

        return [
            _shot_dict(row)
            for row in db.scalars(stmt).all()
        ]
    finally:
        _close_if_needed(db, close)


def get_shot(
    shot_id: str,
    *,
    db: Session | None = None,
) -> Record | None:
    db, close = _get_db(db)
    try:
        row = db.get(Shot, str(shot_id))
        return _shot_dict(row) if row else None
    finally:
        _close_if_needed(db, close)


def get_session_shots(
    session_id: str,
    *,
    db: Session | None = None,
) -> list[Record]:
    return list_shots(
        db=db,
        session_id=session_id,
    )


def get_student_shots(
    student_id: str,
    *,
    db: Session | None = None,
) -> list[Record]:
    return list_shots(
        db=db,
        student_id=student_id,
    )


def next_shot_number(
    session_id: str,
    *,
    db: Session | None = None,
) -> int:
    db, close = _get_db(db)
    try:
        stmt = select(
            func.max(Shot.shot_number)
        ).where(
            Shot.session_id == str(session_id)
        )
        value = db.scalar(stmt)
        return int(value or 0) + 1
    finally:
        _close_if_needed(db, close)


def add_shot(
    shot: Record,
    *,
    db: Session | None = None,
) -> Record:
    db, close = _get_db(db)
    try:
        shot_number = shot.get("shot_number")

        if not shot_number:
            shot_number = next_shot_number(
                str(shot.get("session_id") or ""),
                db=db,
            )

        row = Shot(
            id=str(shot.get("id") or generate_id()),
            session_id=str(shot.get("session_id") or ""),
            student_id=str(shot.get("student_id") or ""),
            shot_number=int(shot_number),
            club=str(shot.get("club") or ""),
            shot_shape=str(shot.get("shot_shape") or ""),
            source=str(shot.get("source") or "Garmin R10"),
            included=bool(shot.get("included", True)),
            ball_speed=shot.get("ball_speed"),
            club_speed=shot.get("club_speed"),
            smash_factor=shot.get("smash_factor"),
            launch_angle=shot.get("launch_angle"),
            launch_direction=shot.get("launch_direction"),
            spin_rate=shot.get("spin_rate"),
            spin_axis=shot.get("spin_axis"),
            carry_distance=shot.get("carry_distance"),
            total_distance=shot.get("total_distance"),
            apex_height=shot.get("apex_height"),
            attack_angle=shot.get("attack_angle"),
            club_path=shot.get("club_path"),
            club_face=(
                shot.get("club_face")
                if shot.get("club_face") is not None
                else shot.get("face_angle")
            ),
            face_to_path=shot.get("face_to_path"),
            offline_distance=shot.get("offline_distance"),
            raw_signature=str(shot.get("raw_signature") or ""),
        )

        db.add(row)
        db.commit()
        db.refresh(row)
        return _shot_dict(row)
    finally:
        _close_if_needed(db, close)


def create_shot(
    session_id: str = "",
    student_id: str = "",
    *,
    db: Session | None = None,
    **fields: Any,
) -> Record:
    return add_shot(
        {
            "session_id": str(session_id).strip(),
            "student_id": str(student_id).strip(),
            **fields,
        },
        db=db,
    )


def update_shot(
    shot_id: str,
    updates: Record,
    *,
    db: Session | None = None,
) -> Record | None:
    db, close = _get_db(db)
    try:
        row = db.get(Shot, str(shot_id))
        if row is None:
            return None

        allowed = {
            "club",
            "shot_shape",
            "included",
            "ball_speed",
            "club_speed",
            "smash_factor",
            "launch_angle",
            "launch_direction",
            "spin_rate",
            "spin_axis",
            "carry_distance",
            "total_distance",
            "apex_height",
            "attack_angle",
            "club_path",
            "club_face",
            "face_to_path",
            "offline_distance",
        }

        for key, value in updates.items():
            if key in allowed:
                setattr(row, key, value)

        row.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(row)
        return _shot_dict(row)
    finally:
        _close_if_needed(db, close)


def delete_shot(
    shot_id: str,
    *,
    db: Session | None = None,
) -> bool:
    db, close = _get_db(db)
    try:
        row = db.get(Shot, str(shot_id))
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True
    finally:
        _close_if_needed(db, close)


def shot_signature_exists(
    session_id: str,
    signature: str,
    *,
    db: Session | None = None,
) -> bool:
    if not signature:
        return False

    db, close = _get_db(db)
    try:
        stmt = select(Shot.id).where(
            Shot.session_id == str(session_id),
            Shot.raw_signature == str(signature),
        )
        return db.scalar(stmt) is not None
    finally:
        _close_if_needed(db, close)


def get_dashboard_summary(
    db: Session | None = None,
) -> Record:
    db, close = _get_db(db)
    try:
        active_students = db.scalar(
            select(func.count(Student.id)).where(
                Student.status != "Inactive"
            )
        ) or 0

        total_students = db.scalar(
            select(func.count(Student.id))
        ) or 0

        total_sessions = db.scalar(
            select(func.count(CoachingSession.id))
        ) or 0

        total_shots = db.scalar(
            select(func.count(Shot.id))
        ) or 0

        return {
            "active_students": int(active_students),
            "total_students": int(total_students),
            "total_sessions": int(total_sessions),
            "total_shots": int(total_shots),
            "pending_import_count": 0,
        }
    finally:
        _close_if_needed(db, close)


def get_store_summary() -> Record:
    return get_dashboard_summary()


def refresh_session_shot_count(
    session_id: str,
    *,
    db: Session | None = None,
) -> int:
    db, close = _get_db(db)
    try:
        count = db.scalar(
            select(func.count(Shot.id)).where(
                Shot.session_id == str(session_id)
            )
        ) or 0
        return int(count)
    finally:
        _close_if_needed(db, close)
