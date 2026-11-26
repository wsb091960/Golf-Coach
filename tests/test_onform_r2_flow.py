"""Authenticated Onform upload/re-OCR flows against isolated SQLite and fake R2.

These exercise media delivery and persistence; OCR values are posted as the
browser OCR client would submit them. No OCR recognition accuracy is asserted.
"""
import base64
import hashlib
import io
import json
import os
import tempfile
import unittest
import zipfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models import CoachingSession, SessionVideo, Student, SwingAnalysis, SwingCheckpoint
from app.routers import auth, swing_analysis_workspace as workspace
from app.services.media_storage import MediaStore
from app.swing_analysis_store import create_analysis


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aL9sAAAAASUVORK5CYII=')


class Missing(Exception):
    response = {'Error': {'Code': 'NoSuchKey'}}


class FakeR2:
    def __init__(self):
        self.objects = {}
        self.head_error = None
        self.deletions = []

    def put_object(self, **kw):
        self.objects[kw['Key']] = {key: kw[key] for key in ('Body', 'ContentType', 'Metadata')}

    def head_object(self, **kw):
        if self.head_error:
            raise self.head_error
        if kw['Key'] not in self.objects:
            raise Missing()
        item = self.objects[kw['Key']]
        return {'ContentLength': len(item['Body']), 'ContentType': item['ContentType'], 'Metadata': item['Metadata']}

    def get_object(self, **kw):
        if kw['Key'] not in self.objects:
            raise Missing()
        return {'Body': io.BytesIO(self.objects[kw['Key']]['Body'])}

    def delete_object(self, **kw):
        self.deletions.append(kw['Key'])
        self.objects.pop(kw['Key'], None)


class OnformR2FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.media_root = Path(self.temp.name)/'screenshots'
        self.media_root.mkdir()
        self.env = patch.dict(os.environ, {'MEDIA_STORAGE_BACKEND': 'r2', 'R2_BUCKET': 'private',
            'R2_PREFIX': 'golf-coach', 'GOLF_PUBLIC_URL': 'https://testserver',
            'GOLF_OWNER_EMAIL': 'coach@example.test'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.remote = FakeR2()
        self.storage = MediaStore('onform_screenshots', self.media_root, self.remote)
        self.media_patch = patch.object(workspace, 'ONFORM_STORAGE', self.storage)
        self.media_patch.start()
        self.addCleanup(self.media_patch.stop)
        self.engine = create_engine('sqlite:///' + str(Path(self.temp.name)/'flow.db'),
            connect_args={'check_same_thread': False})
        self.addCleanup(self.engine.dispose)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)
        token = 'a'*64
        with self.sessions() as db:
            db.add(Student(id='student', first_name='Test', last_name='Golfer'))
            db.add(CoachingSession(id='session', student_id='student'))
            db.add(SessionVideo(id='original', session_id='session', student_id='student',
                video_type='original_swing', stored_filename='original.mp4'))
            db.add(auth.GolfSession(token_hash=auth.digest(token), owner_email='coach@example.test',
                expires_at=auth.now_utc()+timedelta(hours=1)))
            db.commit()
            analysis = create_analysis(db, 'original')
            self.analysis_id = analysis.id
        self.auth_patch = patch.object(auth, 'SessionLocal', self.sessions)
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)
        app = FastAPI()
        app.add_middleware(auth.GolfOwnerAuthMiddleware)
        app.include_router(workspace.router)
        def isolated_db():
            with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = isolated_db
        self.client = TestClient(app, base_url='https://testserver')
        self.addCleanup(self.client.close)
        self.client.cookies.set(auth.SESSION_COOKIE, token)
        self.headers = {'Origin': 'https://testserver'}

    def url(self, suffix):
        return f'/swing-analysis/{self.analysis_id}/workspace/{suffix}'

    def single_import(self, **kwargs):
        return self.client.post(self.url('onform-screenshot'), headers=self.headers,
            files={'screenshot_1': ('metrics.png', PNG, 'image/png'),
                   'screenshot_2': ('body.png', PNG, 'image/png')},
            data={'metrics_json': json.dumps({'pelvis_rotation': 28, 'torso_rotation': -11}),
                  'ocr_text_2': 'Torso Forward Bend 31', **kwargs})

    def test_saved_ocr_screenshots_reopen_and_reuse_r2_without_reupload(self):
        saved = self.single_import()
        self.assertEqual(saved.status_code, 200, saved.text)
        imported = saved.json()['saved_import']
        self.assertEqual(len(imported['screenshots']), 2)
        self.assertEqual(list(self.media_root.iterdir()), [])
        for item in imported['screenshots']:
            self.assertTrue(item['available'])
            self.assertEqual(item['sha256'], hashlib.sha256(PNG).hexdigest())
            self.assertEqual(item['size_bytes'], len(PNG))
            # This is the same protected URL used by browser OCR/canvas reads.
            readback = self.client.get(item['url'])
            self.assertEqual(readback.status_code, 200)
            self.assertEqual(readback.content, PNG)
            self.assertTrue(readback.headers['content-type'].startswith('image/png'))
        verified = self.client.post(self.url('onform-screenshot'), headers=self.headers,
            data={'verified': 'true', 'checkpoint_position': 'P7',
                'metrics_json': json.dumps({'pelvis_rotation': 30, 'torso_forward_bend': 31}),
                'ocr_text_2': 'Torso Forward Bend 31'})
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertEqual(len(self.remote.objects), 2)
        with self.sessions() as db:
            analysis = db.get(SwingAnalysis, self.analysis_id)
            latest = workspace._latest_onform_import(analysis)
            self.assertEqual(latest['metrics']['torso_forward_bend'], 31)
            self.assertTrue(latest['verified'])
            self.assertEqual(len(json.loads(analysis.extra_metrics_json)['onform_screenshot_imports']), 2)
            checkpoint = db.scalar(select(SwingCheckpoint).where(
                SwingCheckpoint.analysis_id == self.analysis_id, SwingCheckpoint.position == 'P7'))
            self.assertEqual(checkpoint.pelvis_rotation, 30)
            for item in latest['screenshots']:
                self.assertTrue(item['available'])
                self.assertEqual(item['sha256'], hashlib.sha256(PNG).hexdigest())
                self.assertEqual(item['size_bytes'], len(PNG))

    def test_all_ten_position_images_and_forward_bend_survive_reload(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            for i in range(1, 11):
                archive.writestr(f'P{i}.png', PNG)
        uploaded = self.client.post(self.url('onform-p-position-bundle'), headers=self.headers,
            files={'bundle': ('positions.zip', buffer.getvalue(), 'application/zip')})
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        screenshots = uploaded.json()['saved_import']['screenshots']
        self.assertEqual([item['position'] for item in screenshots], [f'P{i}' for i in range(1, 11)])
        values = {'P4': {'torso_rotation': 98, 'pelvis_rotation': 40, 'torso_forward_bend': 35},
                  'P7': {'torso_rotation': -11, 'pelvis_rotation': 28, 'torso_forward_bend': 31}}
        stored = self.client.post(self.url('onform-p-position-metrics'), headers=self.headers,
            data={'position_metrics_json': json.dumps(values), 'verified': 'true',
                  'position_sequence_text_json': json.dumps({'P7': 'Torso Forward Bend 31'})})
        self.assertEqual(stored.status_code, 200, stored.text)
        with self.sessions() as db:
            analysis = db.get(SwingAnalysis, self.analysis_id)
            latest = workspace._latest_onform_import(analysis)
            self.assertEqual(latest['position_metrics'], values)
            self.assertEqual(latest['kinematic_sequence']['ocr_text_by_position']['P7'], 'Torso Forward Bend 31')
            checkpoint = db.scalar(select(SwingCheckpoint).where(
                SwingCheckpoint.analysis_id == self.analysis_id, SwingCheckpoint.position == 'P7'))
            self.assertEqual(json.loads(checkpoint.extra_metrics_json)['onform_metrics']['torso_forward_bend'], 31)
        self.assertEqual(len(self.remote.objects), 10)
        self.assertEqual(list(self.media_root.iterdir()), [])
        for item in screenshots:
            self.assertEqual(self.client.get(item['url']).content, PNG)

    def test_legacy_local_screenshots_remain_readable_after_enabling_r2(self):
        with patch.dict(os.environ, {'MEDIA_STORAGE_BACKEND': 'local'}):
            saved = self.single_import()
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.remote.objects, {})
        for item in saved.json()['saved_import']['screenshots']:
            response = self.client.get(item['url'])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, PNG)
        with self.sessions() as db:
            self.assertTrue(all(item['available'] for item in workspace._latest_onform_import(
                db.get(SwingAnalysis, self.analysis_id))['screenshots']))

    def test_screenshot_urls_require_login_and_analysis_ownership(self):
        saved = self.single_import()
        self.assertEqual(saved.status_code, 200, saved.text)
        url = saved.json()['saved_import']['screenshots'][0]['url']
        self.client.cookies.clear()
        denied = self.client.get(url)
        self.assertEqual(denied.status_code, 401)
        self.client.cookies.set(auth.SESSION_COOKIE, 'a'*64)
        wrong_prefix = url.rsplit('/', 1)[0]+'/other-session_other-analysis_source.png'
        self.assertEqual(self.client.get(wrong_prefix).status_code, 404)

    def test_rejected_partial_upload_cleans_only_uncommitted_media(self):
        result = self.client.post(self.url('onform-screenshot'), headers=self.headers,
            files={'screenshot_1': ('metrics.png', PNG, 'image/png')})
        self.assertEqual(result.status_code, 422)
        self.assertEqual(self.remote.objects, {})
        self.assertEqual(len(self.remote.deletions), 1)
        with self.sessions() as db:
            analysis = db.get(SwingAnalysis, self.analysis_id)
            self.assertEqual(json.loads(analysis.extra_metrics_json).get('onform_screenshot_imports', []), [])

    def test_post_commit_storage_outage_does_not_delete_committed_evidence(self):
        # Initial import has no previous screenshots, so the first HEAD occurs
        # only when constructing the response after db.commit().
        self.remote.head_error = OSError('temporary R2 outage')
        result = self.single_import()
        self.assertEqual(result.status_code, 503)
        self.remote.head_error = None
        with self.sessions() as db:
            analysis = db.get(SwingAnalysis, self.analysis_id)
            saved = json.loads(analysis.extra_metrics_json)['onform_screenshot_imports'][-1]
            self.assertEqual(len(saved['screenshots']), 2)
            for item in saved['screenshots']:
                self.assertTrue(self.storage.exists(item['stored_filename']))
                self.assertEqual(self.client.get(self.url('onform-screenshot/')+item['stored_filename']).content, PNG)
        self.assertEqual(self.remote.deletions, [])


if __name__ == '__main__':
    unittest.main()
