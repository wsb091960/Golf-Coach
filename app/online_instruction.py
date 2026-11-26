"""Invite-only student access and persistent records for the online lesson pilot.

Student credentials never authorize existing coach routes. Published lesson
snapshots are separate from editable coach drafts and private coach notes.
"""
from datetime import timedelta
import re

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base, SessionLocal
from app.routers.auth import digest, now_utc

STUDENT_COOKIE = '__Host-golf_student'
STUDENT_SESSION_SECONDS = 14 * 24 * 60 * 60
INVITE_SECONDS = 7 * 24 * 60 * 60
STATUSES = {
    'draft': 'Add your swing', 'submitted': 'Submitted',
    'needs_view': 'Another view requested', 'in_review': 'In review',
    'lesson_ready': 'Lesson ready', 'follow_up_due': 'Follow-up due',
}


class StudentInvite(Base):
    __tablename__ = 'online_student_invites'
    token_hash = Column(String(64), primary_key=True)
    student_id = Column(String(64), ForeignKey('students.id'), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)


class StudentSession(Base):
    __tablename__ = 'online_student_sessions'
    token_hash = Column(String(64), primary_key=True)
    student_id = Column(String(64), ForeignKey('students.id'), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)


class OnlineSubmission(Base):
    __tablename__ = 'online_submissions'
    id = Column(String(64), primary_key=True)
    request_key = Column(String(64), nullable=False, unique=True)
    student_id = Column(String(64), ForeignKey('students.id'), nullable=False, index=True)
    session_id = Column(String(64), ForeignKey('sessions.id'), nullable=False)
    parent_id = Column(String(64), ForeignKey('online_submissions.id'))
    goal = Column(Text, nullable=False)
    usual_miss = Column(Text, default='')
    club = Column(String(100), default='')
    handedness = Column(String(20), default='Unknown')
    practice_access = Column(Text, default='')
    limitations = Column(Text, default='')
    status = Column(String(30), default='draft', nullable=False, index=True)
    created_at = Column(DateTime, default=now_utc, nullable=False)
    submitted_at = Column(DateTime)
    draft_summary = Column(Text, default='')
    draft_priority = Column(Text, default='')
    draft_drills = Column(Text, default='')
    draft_test = Column(Text, default='')
    draft_recording_id = Column(String(64))
    coach_notes = Column(Text, default='')


class OnlineMedia(Base):
    __tablename__ = 'online_media'
    id = Column(String(64), primary_key=True)
    submission_id = Column(String(64), ForeignKey('online_submissions.id'), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    view = Column(String(30), default='')
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(100), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=now_utc, nullable=False)


class PublishedLesson(Base):
    __tablename__ = 'online_published_lessons'
    id = Column(String(64), primary_key=True)
    submission_id = Column(String(64), ForeignKey('online_submissions.id'), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    priority = Column(Text, nullable=False)
    drills = Column(Text, nullable=False)
    practice_test = Column(Text, nullable=False)
    recording_id = Column(String(64))
    published_at = Column(DateTime, default=now_utc, nullable=False)


class OnlineMessage(Base):
    __tablename__ = 'online_messages'
    id = Column(String(64), primary_key=True)
    submission_id = Column(String(64), ForeignKey('online_submissions.id'), nullable=False, index=True)
    author = Column(String(20), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now_utc, nullable=False)


class OnlineStorageProbe(Base):
    """One non-student marker for an explicit database/media durability check."""
    __tablename__ = 'online_storage_probe'
    id = Column(String(20), primary_key=True)
    marker_hash = Column(String(64), nullable=False)


def student_endpoint(path):
    return path == '/learn' or path.startswith('/learn/')


def invite_endpoint(path, method):
    return bool(re.fullmatch(r'/learn/invite/[a-f0-9]{64}', path)) and method in {'GET', 'HEAD', 'POST'}


def student_for_cookie(request):
    token = request.cookies.get(STUDENT_COOKIE, '')
    if not re.fullmatch(r'[a-f0-9]{64}', token):
        return None
    with SessionLocal() as db:
        session = db.get(StudentSession, digest(token))
        if session and session.expires_at > now_utc():
            # Deleted students cannot retain portal access, even on SQLite
            # installations which do not enable foreign-key enforcement.
            from app.models import Student
            if db.get(Student, session.student_id):
                return session.student_id
    return None
