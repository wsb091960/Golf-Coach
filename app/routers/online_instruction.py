"""First online-instruction slice: invite, submit, review, publish, follow up."""
from datetime import datetime, timedelta
import hashlib
import os
from pathlib import Path
import re
import secrets
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student, CoachingSession
from app.online_instruction import (
    INVITE_SECONDS, STUDENT_COOKIE, STUDENT_SESSION_SECONDS, STATUSES,
    OnlineMedia, OnlineMessage, OnlineSubmission, PublishedLesson,
    StudentInvite, StudentSession,
)
from app.routers.auth import digest, now_utc, public_origin

router = APIRouter(tags=['Online Instruction'])
templates = Jinja2Templates(directory='app/templates')
FORMATS = {'.mp4': 'video/mp4', '.mov': 'video/quicktime', '.webm': 'video/webm',
           '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}


def text(value, limit=4000, required=False):
    value = value.strip()
    if len(value) > limit or (required and not value):
        raise HTTPException(422, 'Please complete the required fields and keep your response within the stated length.')
    return value


def student_id(request):
    value = getattr(request.state, 'golf_student', None)
    if not value:
        raise HTTPException(401, 'Ask your coach for a new student access link.')
    return value


def owner(request):
    if not getattr(request.state, 'golf_owner', None):
        raise HTTPException(403, 'Coach access required.')


def submission(db, identity, request, coach=False):
    if coach:
        owner(request)
    row = db.get(OnlineSubmission, identity)
    if not row or not db.get(Student, row.student_id):
        raise HTTPException(404, 'Lesson not found.')
    if not coach and row.student_id != student_id(request):
        raise HTTPException(404, 'Lesson not found.')
    return row


def media_root():
    # No fallback into the repository or ephemeral app/media directories.
    configured = os.getenv('ONLINE_INSTRUCTION_MEDIA_DIR', '').strip()
    if not configured or not Path(configured).is_absolute():
        raise HTTPException(503, 'Uploads are being prepared. Please contact your coach.')
    return Path(configured).resolve()


def context(request, **values):
    return dict(request=request, statuses=STATUSES, **values)


def detail_context(db, row):
    return dict(
        submission=row, student=db.get(Student, row.student_id),
        evidence=db.scalars(select(OnlineMedia).where(
            OnlineMedia.submission_id == row.id, OnlineMedia.role == 'evidence'
        ).order_by(OnlineMedia.created_at)).all(),
        lessons=db.scalars(select(PublishedLesson).where(
            PublishedLesson.submission_id == row.id
        ).order_by(PublishedLesson.published_at.desc(), PublishedLesson.id)).all(),
        messages=db.scalars(select(OnlineMessage).where(
            OnlineMessage.submission_id == row.id
        ).order_by(OnlineMessage.created_at, OnlineMessage.id)).all(),
        storage_ready=bool(os.getenv('ONLINE_INSTRUCTION_MEDIA_DIR', '').startswith('/')),
    )


@router.get('/online-instruction')
def coach_queue(request: Request, db: Session = Depends(get_db)):
    owner(request)
    rows = db.execute(select(OnlineSubmission, Student).join(
        Student, OnlineSubmission.student_id == Student.id
    ).order_by(OnlineSubmission.created_at.desc())).all()
    return templates.TemplateResponse(request=request, name='online_coach.html', context=context(
        request, rows=rows, students=db.scalars(select(Student).order_by(Student.first_name)).all(),
        page_title='Online Instruction', mode='queue',
        storage_ready=bool(os.getenv('ONLINE_INSTRUCTION_MEDIA_DIR', '').startswith('/')),
    ))


@router.post('/online-instruction/invites')
def create_invite(request: Request, student: str = Form(...), db: Session = Depends(get_db)):
    owner(request)
    row = db.get(Student, student)
    if not row:
        raise HTTPException(404, 'Student not found.')
    # A fresh link replaces outstanding unused links. Existing sessions remain
    # until expiry or the coach explicitly revokes access below.
    db.execute(delete(StudentInvite).where(StudentInvite.student_id == student))
    token = secrets.token_hex(32)
    db.add(StudentInvite(token_hash=digest(token), student_id=student,
                         expires_at=now_utc() + timedelta(seconds=INVITE_SECONDS)))
    db.commit()
    return templates.TemplateResponse(request=request, name='online_coach.html', context=context(
        request, mode='invite', student=row, invite_url=public_origin() + '/learn/invite/' + token,
        page_title='Student access link',
    ))


@router.post('/online-instruction/students/{identity}/revoke')
def revoke_access(identity: str, request: Request, db: Session = Depends(get_db)):
    owner(request)
    db.execute(delete(StudentInvite).where(StudentInvite.student_id == identity))
    db.execute(delete(StudentSession).where(StudentSession.student_id == identity))
    db.commit()
    return RedirectResponse('/online-instruction?message=Student+access+revoked.', 303)


@router.get('/learn/invite/{token}')
def invite_page(token: str, request: Request, db: Session = Depends(get_db)):
    row = db.get(StudentInvite, digest(token))
    valid = row and row.used_at is None and row.expires_at > now_utc() and db.get(Student, row.student_id)
    return templates.TemplateResponse(request=request, name='online_student.html',
        context=context(request, mode='invite', valid=bool(valid)), status_code=200 if valid else 410)


@router.post('/learn/invite/{token}')
def redeem_invite(token: str, request: Request, db: Session = Depends(get_db)):
    now = now_utc()
    row = db.get(StudentInvite, digest(token))
    if not row or not db.get(Student, row.student_id):
        raise HTTPException(410, 'This link has expired. Ask your coach for another.')
    # Atomic redemption prevents reuse by concurrent clients.
    used = db.execute(update(StudentInvite).where(
        StudentInvite.token_hash == digest(token), StudentInvite.used_at.is_(None),
        StudentInvite.expires_at > now,
    ).values(used_at=now))
    if used.rowcount != 1:
        db.rollback()
        raise HTTPException(410, 'This link has expired or has already been used.')
    session_token = secrets.token_hex(32)
    db.add(StudentSession(token_hash=digest(session_token), student_id=row.student_id,
                          expires_at=now + timedelta(seconds=STUDENT_SESSION_SECONDS)))
    db.commit()
    response = RedirectResponse('/learn', 303)
    response.set_cookie(STUDENT_COOKIE, session_token, max_age=STUDENT_SESSION_SECONDS,
                        secure=True, httponly=True, samesite='lax', path='/')
    return response


@router.post('/learn/logout')
def student_logout(request: Request, db: Session = Depends(get_db)):
    db.execute(delete(StudentSession).where(
        StudentSession.token_hash == digest(request.cookies.get(STUDENT_COOKIE, ''))))
    db.commit()
    response = RedirectResponse('/', 303)
    response.delete_cookie(STUDENT_COOKIE, path='/', secure=True, httponly=True, samesite='lax')
    return response


@router.get('/learn')
def student_home(request: Request, db: Session = Depends(get_db)):
    identity = student_id(request)
    return templates.TemplateResponse(request=request, name='online_student.html', context=context(
        request, mode='home', student=db.get(Student, identity), request_key=str(uuid4()),
        rows=db.scalars(select(OnlineSubmission).where(OnlineSubmission.student_id == identity)
                        .order_by(OnlineSubmission.created_at.desc())).all(),
    ))


@router.post('/learn/submissions')
def create_submission(request: Request, request_key: str = Form(...), goal: str = Form(...),
        club: str = Form(''), usual_miss: str = Form(''), handedness: str = Form('Unknown'),
        practice_access: str = Form(''), limitations: str = Form(''), parent_id: str = Form(''),
        db: Session = Depends(get_db)):
    identity = student_id(request)
    try:
        key = str(UUID(request_key))
    except ValueError:
        raise HTTPException(422, 'Refresh the page and try again.')
    old = db.scalar(select(OnlineSubmission).where(OnlineSubmission.request_key == key))
    if old:
        if old.student_id != identity:
            raise HTTPException(409, 'Refresh the page and try again.')
        return RedirectResponse('/learn/submissions/' + old.id, 303)
    if parent_id:
        previous = submission(db, parent_id, request)
        if not db.scalar(select(PublishedLesson.id).where(PublishedLesson.submission_id == previous.id)):
            raise HTTPException(422, 'Follow-ups need an existing published lesson.')
    if handedness not in {'Right', 'Left', 'Unknown'}:
        raise HTTPException(422, 'Choose your handedness.')
    session_key, row_key = str(uuid4()), str(uuid4())
    clean_goal, clean_club = text(goal, required=True), text(club, 100)
    db.add(CoachingSession(id=session_key, student_id=identity, session_type='Online Instruction',
                          name='Online swing review', primary_club=clean_club,
                          session_date=datetime.now(ZoneInfo('America/Los_Angeles')).date()))
    row = OnlineSubmission(id=row_key, request_key=key, student_id=identity, session_id=session_key,
        parent_id=parent_id or None, goal=clean_goal, club=clean_club, usual_miss=text(usual_miss),
        handedness=handedness, practice_access=text(practice_access), limitations=text(limitations))
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        old = db.scalar(select(OnlineSubmission).where(OnlineSubmission.request_key == key,
                                                      OnlineSubmission.student_id == identity))
        if not old:
            raise
        row_key = old.id
    return RedirectResponse('/learn/submissions/' + row_key, 303)


@router.get('/learn/submissions/{identity}')
def student_detail(identity: str, request: Request, db: Session = Depends(get_db)):
    row = submission(db, identity, request)
    values = detail_context(db, row)
    # Do not pass the editable submission ORM object to the student template.
    values['submission'] = {key: getattr(row, key) for key in (
        'id', 'goal', 'club', 'usual_miss', 'handedness', 'practice_access',
        'limitations', 'status', 'parent_id', 'created_at', 'submitted_at')}
    return templates.TemplateResponse(request=request, name='online_student.html',
        context=context(request, mode='detail', request_key=str(uuid4()), **values))


@router.get('/online-instruction/{identity}')
def coach_detail(identity: str, request: Request, db: Session = Depends(get_db)):
    row = submission(db, identity, request, coach=True)
    recordings = db.scalars(select(OnlineMedia).where(
        OnlineMedia.submission_id == identity, OnlineMedia.role == 'feedback'
    ).order_by(OnlineMedia.created_at.desc())).all()
    return templates.TemplateResponse(request=request, name='online_coach.html', context=context(
        request, mode='detail', page_title='Online swing review', recordings=recordings, **detail_context(db, row)))


def matches_file(header, extension):
    if extension in {'.jpg', '.jpeg'}:
        return header.startswith(b'\xff\xd8\xff')
    if extension == '.png':
        return header.startswith(b'\x89PNG\r\n\x1a\n')
    if extension == '.webm':
        return header.startswith(b'\x1aE\xdf\xa3')
    return header[4:8] == b'ftyp' or (extension == '.mov' and header[4:8] in {b'moov', b'wide', b'mdat'})


async def save_media(db, row, upload, role, view):
    if role == 'evidence' and row.status not in {'draft', 'needs_view'}:
        raise HTTPException(409, 'This swing is already submitted. Start a follow-up for new evidence.')
    if view not in {'Face-on', 'Down-the-line', 'Other'}:
        raise HTTPException(422, 'Choose a camera view.')
    count = len(db.scalars(select(OnlineMedia.id).where(
        OnlineMedia.submission_id == row.id, OnlineMedia.role == role)).all())
    if count >= (6 if role == 'evidence' else 12):
        raise HTTPException(422, 'The attachment limit for this lesson has been reached.')
    original = (upload.filename or '').replace('\\', '/').split('/')[-1]
    if not original or len(original) > 255 or any(ord(c) < 32 for c in original):
        raise HTTPException(422, 'Choose a file with a valid filename.')
    extension = Path(original).suffix.lower()
    if extension not in FORMATS or (role == 'feedback' and not FORMATS[extension].startswith('video/')):
        raise HTTPException(422, 'Use MP4, MOV or WEBM video, or a JPG/PNG screenshot.')
    root = media_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = uuid4().hex + extension
    target = root / name
    temp = root / (name + '.part')
    size, checksum = 0, hashlib.sha256()
    maximum = (10 if FORMATS[extension].startswith('image/') else 100) * 1024 * 1024
    try:
        with temp.open('xb') as stream:
            os.chmod(temp, 0o600)
            first = True
            while chunk := await upload.read(1024 * 1024):
                if first:
                    if not matches_file(chunk[:32], extension):
                        raise HTTPException(422, 'The file does not match the selected video or image format.')
                    first = False
                size += len(chunk)
                if size > maximum:
                    raise HTTPException(413, 'Use a video under 100 MB or an image under 10 MB.')
                checksum.update(chunk)
                stream.write(chunk)
        if not size:
            raise HTTPException(422, 'The selected file is empty.')
        duplicate = db.scalar(select(OnlineMedia).where(
            OnlineMedia.submission_id == row.id, OnlineMedia.role == role,
            OnlineMedia.view == view, OnlineMedia.sha256 == checksum.hexdigest()))
        if duplicate:
            temp.unlink(missing_ok=True)
            if role == 'feedback':
                row.draft_recording_id = duplicate.id
                db.commit()
            return
        temp.replace(target)
        record = OnlineMedia(id=str(uuid4()), submission_id=row.id, role=role, view=view,
            original_name=original, stored_name=name, content_type=FORMATS[extension],
            size_bytes=size, sha256=checksum.hexdigest())
        db.add(record)
        if role == 'feedback':
            row.draft_recording_id = record.id
        db.commit()
    except Exception:
        db.rollback()
        temp.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


@router.post('/learn/submissions/{identity}/media')
async def student_upload(identity: str, request: Request, file: UploadFile = File(...),
        view: str = Form('Other'), db: Session = Depends(get_db)):
    row = submission(db, identity, request)
    await save_media(db, row, file, 'evidence', view)
    return RedirectResponse('/learn/submissions/' + identity, 303)


@router.post('/online-instruction/{identity}/recording')
async def coach_upload(identity: str, request: Request, file: UploadFile = File(...),
        db: Session = Depends(get_db)):
    row = submission(db, identity, request, coach=True)
    await save_media(db, row, file, 'feedback', 'Other')
    return RedirectResponse('/online-instruction/' + identity, 303)


@router.get('/learn/media/{identity}')
@router.get('/online-instruction/media/{identity}')
def serve_media(identity: str, request: Request, db: Session = Depends(get_db)):
    coach = request.url.path.startswith('/online-instruction/')
    record = db.get(OnlineMedia, identity)
    if not record:
        raise HTTPException(404, 'Media not found.')
    submission(db, record.submission_id, request, coach=coach)
    if not coach and record.role == 'feedback' and not db.scalar(select(PublishedLesson.id).where(
        PublishedLesson.submission_id == record.submission_id, PublishedLesson.recording_id == record.id)):
        raise HTTPException(404, 'Media not found.')
    root = media_root()
    path = (root / record.stored_name).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, 'This file is unavailable. Please contact your coach.')
    return FileResponse(path, media_type=record.content_type, filename=record.original_name,
                        content_disposition_type='inline')


@router.post('/learn/submissions/{identity}/submit')
def submit_swing(identity: str, request: Request, db: Session = Depends(get_db)):
    row = submission(db, identity, request)
    if row.status not in {'draft', 'needs_view'}:
        return RedirectResponse('/learn/submissions/' + identity, 303)
    if not db.scalar(select(OnlineMedia.id).where(OnlineMedia.submission_id == identity,
                                                 OnlineMedia.role == 'evidence')):
        raise HTTPException(422, 'Upload at least one swing video or screenshot first.')
    row.status, row.submitted_at = 'submitted', now_utc()
    db.commit()
    return RedirectResponse('/learn/submissions/' + identity, 303)


@router.post('/online-instruction/{identity}/review')
def save_review(identity: str, request: Request, summary: str = Form(''), priority: str = Form(''),
        drills: str = Form(''), practice_test: str = Form(''), coach_notes: str = Form(''),
        recording_id: str = Form(''), action: str = Form('save'), db: Session = Depends(get_db)):
    row = submission(db, identity, request, coach=True)
    if action not in {'save', 'publish'}:
        raise HTTPException(422, 'Choose Save or Publish.')
    if recording_id:
        recording = db.get(OnlineMedia, recording_id)
        if not recording or recording.submission_id != identity or recording.role != 'feedback':
            raise HTTPException(422, 'Choose a recording attached to this lesson.')
    row.draft_summary, row.draft_priority = text(summary), text(priority)
    row.draft_drills, row.draft_test = text(drills), text(practice_test)
    row.coach_notes, row.draft_recording_id = text(coach_notes), recording_id or None
    if action == 'publish':
        if row.status == 'draft' or not all((row.draft_summary, row.draft_priority, row.draft_drills, row.draft_test)):
            raise HTTPException(422, 'Wait for submission and complete the summary, priority, drills, and practice test before publishing.')
        db.add(PublishedLesson(id=str(uuid4()), submission_id=identity, summary=row.draft_summary,
            priority=row.draft_priority, drills=row.draft_drills, practice_test=row.draft_test,
            recording_id=row.draft_recording_id))
        row.status = 'lesson_ready'
    db.commit()
    return RedirectResponse('/online-instruction/' + identity, 303)


@router.post('/online-instruction/{identity}/status')
def change_status(identity: str, request: Request, status: str = Form(...), db: Session = Depends(get_db)):
    row = submission(db, identity, request, coach=True)
    if status not in {'in_review', 'needs_view', 'follow_up_due'} or row.status == 'draft':
        raise HTTPException(422, 'Choose a valid status for a submitted swing.')
    if status == 'follow_up_due' and not db.scalar(select(PublishedLesson.id).where(PublishedLesson.submission_id == identity)):
        raise HTTPException(422, 'Publish a lesson before requesting a follow-up.')
    row.status = status
    db.commit()
    return RedirectResponse('/online-instruction/' + identity, 303)


@router.post('/learn/submissions/{identity}/messages')
@router.post('/online-instruction/{identity}/messages')
def add_message(identity: str, request: Request, message: str = Form(...), db: Session = Depends(get_db)):
    coach = request.url.path.startswith('/online-instruction/')
    submission(db, identity, request, coach=coach)
    db.add(OnlineMessage(id=str(uuid4()), submission_id=identity,
                         author='coach' if coach else 'student', text=text(message, required=True)))
    db.commit()
    prefix = '/online-instruction/' if coach else '/learn/submissions/'
    return RedirectResponse(prefix + identity + '#questions', 303)
