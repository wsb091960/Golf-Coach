"""Isolated, real HTTP permission and lesson-delivery tests; no live student data."""
import base64
from datetime import timedelta
from pathlib import Path
import re
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
import pytest

from app.database import Base, get_db
from app.models import Student
from app.routers import auth
from app import online_instruction as models
from app.routers.online_instruction import router
from app.routers.public_home import router as public_router

ORIGIN = 'https://golf.test'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJKkAAAAASUVORK5CYII=')
VIDEO = b'\x00\x00\x00\x18ftypisom' + b'\x00' * 32


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    monkeypatch.setenv('ONLINE_INSTRUCTION_ENABLED', '1')
    monkeypatch.setenv('ONLINE_INSTRUCTION_MEDIA_DIR', str(tmp_path / 'private-media'))
    monkeypatch.setenv('GOLF_PUBLIC_URL', ORIGIN)
    engine = create_engine('sqlite:///' + str(tmp_path / 'test.db'), connect_args={'check_same_thread': False})
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(auth, 'SessionLocal', factory)
    monkeypatch.setattr(models, 'SessionLocal', factory)
    Base.metadata.create_all(engine)
    with factory() as db:
        db.add_all([Student(id='a', first_name='Alex'), Student(id='b', first_name='Blair')])
        db.add(auth.GolfSession(token_hash=auth.digest('a' * 64), owner_email=auth.owner_email(),
                                expires_at=auth.now_utc() + timedelta(hours=1)))
        for sid, token in [('a', 'b' * 64), ('b', 'c' * 64)]:
            db.add(models.StudentSession(token_hash=auth.digest(token), student_id=sid,
                                          expires_at=auth.now_utc() + timedelta(days=1)))
        db.commit()
    app = FastAPI()
    app.add_middleware(auth.GolfOwnerAuthMiddleware)
    app.include_router(auth.router)
    app.include_router(router)
    app.include_router(public_router)
    @app.get('/dashboard', name='dashboard')
    def dashboard():
        return {'private': True}
    @app.get('/sessions/secret')
    def secret():
        return {'private': True}
    def database():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = database
    clients = [TestClient(app, base_url=ORIGIN, headers={'Origin': ORIGIN}) for _ in range(4)]
    coach, alex, blair, visitor = clients
    coach.cookies.set(auth.SESSION_COOKIE, 'a' * 64)
    alex.cookies.set(models.STUDENT_COOKIE, 'b' * 64)
    blair.cookies.set(models.STUDENT_COOKIE, 'c' * 64)
    yield dict(coach=coach, alex=alex, blair=blair, visitor=visitor, db=factory, root=tmp_path / 'private-media')
    for client in clients:
        client.close()
    engine.dispose()


def start(client, **values):
    payload = dict(request_key=str(uuid4()), goal='Improve start line', club='7 iron')
    payload.update(values)
    response = client.post('/learn/submissions', data=payload, follow_redirects=False)
    assert response.status_code == 303
    return response.headers['location'].rsplit('/', 1)[-1]


def upload(client, identity, filename='swing.png', content=PNG):
    return client.post(f'/learn/submissions/{identity}/media', data={'view': 'Face-on'},
        files={'file': (filename, content)}, follow_redirects=False)


def publish(pilot, identity, **values):
    payload = dict(summary='Your setup is the first priority.', priority='Start with alignment.',
                   drills='Use an alignment stick.', practice_test='Count starts through a gate.',
                   coach_notes='PRIVATE-COACH-NOTE', action='publish')
    payload.update(values)
    return pilot['coach'].post(f'/online-instruction/{identity}/review', data=payload, follow_redirects=False)


def submitted(pilot):
    identity = start(pilot['alex'])
    assert upload(pilot['alex'], identity).status_code == 303
    assert pilot['alex'].post(f'/learn/submissions/{identity}/submit', follow_redirects=False).status_code == 303
    return identity


def email_inquiry(pilot, **values):
    payload = dict(request_key=str(uuid4()), sender_email='casey@example.com',
                   first_name='Casey', last_name='Demo', goal='Improve driver start line',
                   club='Driver', source_note='PRIVATE-EMAIL-REFERENCE')
    payload.update(values)
    return pilot['coach'].post('/online-instruction/email-intake', data=payload, follow_redirects=False)


def test_public_email_entry_has_no_login_and_does_not_accept_anonymous_writes(pilot, monkeypatch):
    from html import unescape
    from urllib.parse import urlsplit, parse_qs
    monkeypatch.setenv('GOLF_INQUIRY_EMAIL', 'coach+golf@example.com')
    visitor = pilot['visitor']
    page = visitor.get('/send-your-swing')
    assert page.status_code == 200
    assert 'No account, access code, or Onform' in page.text
    assert '/send-your-swing' in visitor.get('/').text
    href = unescape(re.search(r'href="(mailto:[^"]+)"', page.text).group(1))
    assert 'coach%2Bgolf@example.com' in href
    assert '+' not in urlsplit(href).query  # Mail clients need percent-encoded spaces.
    fields = parse_qs(urlsplit(href).query)
    assert 'My name:\nWhat I would like help with:' in fields['body'][0]
    for client in [visitor, pilot['alex']]:
        assert client.post('/online-instruction/email-intake', data={}).status_code == 401
    assert visitor.post('/send-your-swing', data={}).status_code == 401
    monkeypatch.delenv('ONLINE_INSTRUCTION_ENABLED')
    assert visitor.get('/send-your-swing').status_code == 200
    assert pilot['coach'].post('/online-instruction/email-intake', data={}).status_code == 404


def test_email_inquiry_to_published_student_lesson_without_reupload(pilot):
    response = email_inquiry(pilot)
    assert response.status_code == 303
    path = response.headers['location']
    identity = path.rsplit('/', 1)[-1]
    coach = pilot['coach']
    assert 'PRIVATE-EMAIL-REFERENCE' in coach.get(path).text
    assert coach.post(path + '/email-submit', follow_redirects=False).status_code == 422
    assert coach.post(path + '/email-evidence', data={'view': 'Face-on'},
        files={'file': ('emailed.png', PNG)}, follow_redirects=False).status_code == 303
    assert coach.post(path + '/email-submit', follow_redirects=False).status_code == 303
    assert publish(pilot, identity).status_code == 303
    with pilot['db']() as db:
        row = db.get(models.OnlineSubmission, identity)
        sid = row.student_id
        media = db.scalar(select(models.OnlineMedia).where(models.OnlineMedia.submission_id == identity))
        mid = media.id
        assert row.status == 'lesson_ready'
        assert row.submitted_at is not None
        assert db.get(Student, sid).email == 'casey@example.com'
    invite = coach.post('/online-instruction/invites', data={'student': sid})
    assert 'Open invitation email draft' in invite.text
    url = re.search(r'https://golf.test/learn/invite/[a-f0-9]{64}', invite.text).group()
    visitor = pilot['visitor']
    assert visitor.get('/learn/media/' + mid).status_code == 401
    assert visitor.post(url, follow_redirects=False).status_code == 303
    page = visitor.get('/learn/submissions/' + identity)
    assert page.status_code == 200
    assert 'emailed.png' in page.text and 'Start with alignment.' in page.text
    assert 'PRIVATE-EMAIL-REFERENCE' not in page.text
    assert 'PRIVATE-COACH-NOTE' not in page.text
    assert visitor.get('/learn/media/' + mid).content == PNG
    assert pilot['alex'].get('/learn/submissions/' + identity).status_code == 404
    assert pilot['alex'].get('/learn/media/' + mid).status_code == 404
    assert visitor.post(path + '/email-evidence', files={'file': ('swing.png', PNG)}).status_code == 401
    assert coach.post(path + '/email-evidence', files={'file': ('late.png', PNG)}).status_code == 409


def test_email_intake_retries_identity_checks_and_existing_student(pilot):
    key = str(uuid4())
    first = email_inquiry(pilot, request_key=key)
    assert email_inquiry(pilot, request_key=key).headers['location'] == first.headers['location']
    assert email_inquiry(pilot).status_code == 409  # Explicitly select an existing identity.
    with pilot['db']() as db:
        rows = db.scalars(select(models.OnlineSubmission)).all()
        assert len(rows) == 1
        sid = rows[0].student_id
        assert len(db.scalars(select(Student)).all()) == 3
    assert email_inquiry(pilot, student=sid, sender_email='wrong@example.com').status_code == 409
    assert email_inquiry(pilot, student=sid, sender_email='CASEY@example.com', first_name='').status_code == 303
    assert email_inquiry(pilot, sender_email='not-an-email').status_code == 422
    assert email_inquiry(pilot, sender_email='another@example.com', first_name='').status_code == 422
    assert email_inquiry(pilot, student='missing', sender_email='another@example.com').status_code == 404
    assert pilot['coach'].post('/online-instruction/email-intake', headers={'Origin': 'https://attacker.test'},
        data={'request_key': str(uuid4()), 'sender_email': 'x@example.com', 'goal': 'test'}).status_code == 403
    student_row = start(pilot['alex'])
    assert pilot['coach'].post('/online-instruction/' + student_row + '/email-evidence',
        files={'file': ('swing.png', PNG)}).status_code == 409


def test_emailed_attachment_validation_and_retries(pilot):
    response = email_inquiry(pilot)
    path = response.headers['location']
    endpoint = path + '/email-evidence'
    coach = pilot['coach']
    assert coach.post(endpoint, files={'file': ('bad.png', b'not an image')}).status_code == 422
    assert coach.post(endpoint, files={'file': ('bad.svg', PNG)}).status_code == 422
    assert coach.post(endpoint, files={'file': ('big.png', PNG + b'x' * (10 * 1024 * 1024))}).status_code == 413
    assert not list(pilot['root'].glob('*'))
    for _ in range(2):
        assert coach.post(endpoint, data={'view': 'Face-on'}, files={'file': ('swing.png', PNG)},
                          follow_redirects=False).status_code == 303
    assert coach.post(endpoint, data={'view': 'Down-the-line'}, files={'file': ('swing.mp4', VIDEO)},
                      follow_redirects=False).status_code == 303
    with pilot['db']() as db:
        assert len(db.scalars(select(models.OnlineMedia)).all()) == 2


def test_student_cannot_enter_coach_workspace(pilot):
    alex, visitor = pilot['alex'], pilot['visitor']
    assert alex.get('/learn').status_code == 200
    for path in ['/dashboard', '/sessions/secret', '/online-instruction']:
        assert alex.get(path).status_code == 401
    assert visitor.get('/learn').status_code == 401
    assert pilot['coach'].get('/online-instruction').status_code == 200


def test_disabled_pilot_fails_closed(pilot, monkeypatch):
    monkeypatch.delenv('ONLINE_INSTRUCTION_ENABLED')
    for path in ['/learn', '/online-instruction', '/learn/invite/' + 'd' * 64]:
        assert pilot['alex'].get(path).status_code == 404


def test_one_use_invite_csrf_and_cookie(pilot):
    response = pilot['coach'].post('/online-instruction/invites', data={'student': 'a'})
    url = re.search(r'https://golf.test/learn/invite/[a-f0-9]{64}', response.text).group()
    visitor = pilot['visitor']
    assert visitor.get(url).status_code == 200
    assert visitor.post(url, headers={'Origin': 'https://attacker.test'}, follow_redirects=False).status_code == 403
    assert visitor.get('/learn').status_code == 401
    accepted = visitor.post(url, follow_redirects=False)
    assert accepted.status_code == 303
    cookie = accepted.headers['set-cookie']
    assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=lax' in cookie
    assert visitor.get('/learn').status_code == 200
    assert visitor.post(url, follow_redirects=False).status_code == 410
    assert visitor.get(url).status_code == 410


def test_invite_expiry_and_revocation(pilot):
    with pilot['db']() as db:
        db.add(models.StudentInvite(token_hash=auth.digest('f' * 64), student_id='a',
            expires_at=auth.now_utc() - timedelta(minutes=1)))
        db.commit()
    assert pilot['visitor'].post('/learn/invite/' + 'f' * 64).status_code == 410
    pilot['coach'].post('/online-instruction/students/a/revoke', follow_redirects=False)
    assert pilot['alex'].get('/learn').status_code == 401
    assert pilot['blair'].get('/learn').status_code == 200


def test_creation_retries_do_not_duplicate_sessions(pilot):
    key = str(uuid4())
    first = start(pilot['alex'], request_key=key)
    assert start(pilot['alex'], request_key=key) == first
    response = pilot['blair'].post('/learn/submissions', data={'request_key': key, 'goal': 'Test'})
    assert response.status_code == 409
    with pilot['db']() as db:
        assert len(db.scalars(select(models.OnlineSubmission)).all()) == 1


def test_cross_student_evidence_messages_and_parent_are_denied(pilot):
    identity = submitted(pilot)
    with pilot['db']() as db:
        media = db.scalar(select(models.OnlineMedia)).id
    blair = pilot['blair']
    assert blair.get(f'/learn/submissions/{identity}').status_code == 404
    assert blair.get(f'/learn/media/{media}').status_code == 404
    assert blair.post(f'/learn/submissions/{identity}/messages', data={'message': 'Hi'}).status_code == 404
    assert upload(blair, identity).status_code == 404
    assert blair.post('/learn/submissions', data={'request_key': str(uuid4()), 'goal': 'Follow up', 'parent_id': identity}).status_code == 404


def test_empty_submission_and_file_type_validation(pilot):
    identity = start(pilot['alex'])
    assert pilot['alex'].post(f'/learn/submissions/{identity}/submit').status_code == 422
    assert upload(pilot['alex'], identity, 'bad.png', b'<html>bad</html>').status_code == 422
    assert upload(pilot['alex'], identity, 'bad.svg', PNG).status_code == 422
    assert upload(pilot['alex'], identity, 'empty.png', b'').status_code == 422
    assert not list(pilot['root'].glob('*'))


def test_storage_has_no_ephemeral_fallback(pilot, monkeypatch):
    identity = start(pilot['alex'])
    monkeypatch.delenv('ONLINE_INSTRUCTION_MEDIA_DIR')
    assert upload(pilot['alex'], identity).status_code == 503
    assert not pilot['root'].exists()


def test_oversized_image_is_removed_and_can_be_retried(pilot):
    identity = start(pilot['alex'])
    assert upload(pilot['alex'], identity, 'large.png', PNG + b'x' * (10 * 1024 * 1024)).status_code == 413
    assert not list(pilot['root'].glob('*'))
    assert upload(pilot['alex'], identity).status_code == 303


def test_upload_rejects_public_app_storage(pilot, monkeypatch):
    identity = start(pilot['alex'])
    monkeypatch.setenv('ONLINE_INSTRUCTION_MEDIA_DIR', str(Path('app/static').resolve()))
    assert upload(pilot['alex'], identity).status_code == 503


def test_low_disk_space_cleans_partial_upload(pilot, monkeypatch):
    import shutil
    from types import SimpleNamespace
    identity = start(pilot['alex'])
    monkeypatch.setattr(shutil, 'disk_usage', lambda _: SimpleNamespace(free=1024))
    assert upload(pilot['alex'], identity).status_code == 507
    assert not list(pilot['root'].glob('*'))


def test_expired_student_gets_student_handoff_not_owner_login(pilot):
    response = pilot['visitor'].get('/learn', headers={'Accept': 'text/html'}, follow_redirects=False)
    assert response.status_code == 401
    assert 'Ask William for a fresh link' in response.text
    assert 'Sign in with Google' not in response.text


def test_media_retry_and_stream_access(pilot):
    identity = start(pilot['alex'])
    assert upload(pilot['alex'], identity).status_code == 303
    assert upload(pilot['alex'], identity).status_code == 303
    with pilot['db']() as db:
        rows = db.scalars(select(models.OnlineMedia)).all()
        assert len(rows) == 1
        assert rows[0].size_bytes == len(PNG)
        media = rows[0].id
    response = pilot['alex'].get('/learn/media/' + media)
    assert response.content == PNG
    assert response.headers['cache-control'] == 'no-store'
    assert pilot['visitor'].get('/learn/media/' + media).status_code == 401
    assert pilot['coach'].get('/online-instruction/media/' + media).content == PNG
    assert len(list(pilot['root'].glob('*'))) == 1


def test_published_snapshot_and_recording_stay_separate_from_draft(pilot):
    identity = submitted(pilot)
    response = pilot['coach'].post(f'/online-instruction/{identity}/recording',
        files={'file': ('coach.mp4', VIDEO)}, follow_redirects=False)
    assert response.status_code == 303
    with pilot['db']() as db:
        recording = db.scalar(select(models.OnlineMedia).where(models.OnlineMedia.role == 'feedback')).id
    assert pilot['alex'].get('/learn/media/' + recording).status_code == 404
    assert publish(pilot, identity, action='save', summary='DRAFT-ONLY', recording_id=recording).status_code == 303
    student = pilot['alex'].get('/learn/submissions/' + identity)
    assert 'DRAFT-ONLY' not in student.text and 'PRIVATE-COACH-NOTE' not in student.text
    assert publish(pilot, identity, recording_id=recording).status_code == 303
    student = pilot['alex'].get('/learn/submissions/' + identity)
    assert 'Start with alignment.' in student.text and 'PRIVATE-COACH-NOTE' not in student.text
    assert pilot['alex'].get('/learn/media/' + recording).content == VIDEO
    assert publish(pilot, identity, action='save', summary='UNPUBLISHED-REVISION').status_code == 303
    assert 'UNPUBLISHED-REVISION' not in pilot['alex'].get('/learn/submissions/' + identity).text
    assert pilot['coach'].get('/online-instruction/' + identity).status_code == 200


def test_student_cannot_publish_and_coach_cannot_attach_other_recording(pilot):
    identity = submitted(pilot)
    assert pilot['alex'].post(f'/online-instruction/{identity}/review', data={'action': 'publish'}).status_code == 401
    assert publish(pilot, identity, recording_id='other').status_code == 422
    assert publish(pilot, identity, priority='').status_code == 422


def test_follow_up_and_messages_complete_cycle(pilot):
    identity = submitted(pilot)
    assert publish(pilot, identity).status_code == 303
    response = pilot['alex'].post(f'/learn/submissions/{identity}/messages', data={'message': 'Practiced 20 balls.'})
    assert response.status_code == 200
    assert 'Practiced 20 balls.' in pilot['coach'].get('/online-instruction/' + identity).text
    pilot['coach'].post(f'/online-instruction/{identity}/messages', data={'message': 'Keep the same club.'})
    assert 'Keep the same club.' in pilot['alex'].get('/learn/submissions/' + identity).text
    followup = start(pilot['alex'], parent_id=identity, goal='Practice results: better start line')
    with pilot['db']() as db:
        assert db.get(models.OnlineSubmission, followup).parent_id == identity


def test_mutations_require_origin_and_submitted_evidence_is_locked(pilot):
    identity = submitted(pilot)
    assert upload(pilot['alex'], identity).status_code == 409
    response = pilot['alex'].post(f'/learn/submissions/{identity}/messages',
        data={'message': 'Bad origin'}, headers={'Origin': 'https://attacker.test'})
    assert response.status_code == 403
    assert pilot['coach'].post(f'/online-instruction/{identity}/status', data={'status': 'needs_view'}, follow_redirects=False).status_code == 303
    assert upload(pilot['alex'], identity, 'another.png', PNG + b'new').status_code == 303


def test_email_import_preserves_parent_integrity_and_rolls_back_invalid_input(pilot):
    from sqlalchemy import text as sql_text
    from app.models import CoachingSession
    with pilot['db']() as db:
        db.execute(sql_text('PRAGMA foreign_keys = ON'))
        db.commit()
    assert email_inquiry(pilot, source_note='x' * 4001).status_code == 422
    with pilot['db']() as db:
        assert not db.scalars(select(models.OnlineSubmission)).all()
        assert not db.scalars(select(CoachingSession)).all()
        assert len(db.scalars(select(Student)).all()) == 2
    assert email_inquiry(pilot).status_code == 303
    with pilot['db']() as db:
        assert db.execute(sql_text('PRAGMA foreign_key_check')).all() == []
        assert len(db.scalars(select(models.OnlineEmailIntake)).all()) == 1


def test_invitation_creation_redirects_to_owner_only_preview_without_reissuing(pilot):
    created = pilot['coach'].post('/online-instruction/invites', data={'student': 'a'}, follow_redirects=False)
    assert created.status_code == 303
    preview = created.headers['location']
    first = pilot['coach'].get(preview)
    assert first.status_code == 200
    assert pilot['coach'].get(preview).text == first.text
    assert pilot['visitor'].get(preview).status_code == 401
    assert pilot['alex'].get(preview).status_code == 401
    with pilot['db']() as db:
        assert len(db.scalars(select(models.StudentInvite)).all()) == 1
    token = preview.rsplit('/', 1)[-1]
    assert pilot['visitor'].post('/learn/invite/' + token, follow_redirects=False).status_code == 303
    assert pilot['coach'].get(preview).status_code == 410
