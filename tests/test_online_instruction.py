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
