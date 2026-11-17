import asyncio
import base64
import io
import json
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from app.services import stored_images as images
from app.services import coach_assistant_ai, p_sheet_analyzer
from app.routers import sessions


class FakeR2:
    def __init__(self):
        self.objects = {}
        self.deleted = []

    def put_object(self, **kwargs):
        self.objects[kwargs['Key']] = kwargs['Body']

    def get_object(self, **kwargs):
        return {'Body': io.BytesIO(self.objects[kwargs['Key']])}

    def head_object(self, **kwargs):
        return {'ContentLength': len(self.objects[kwargs['Key']]), 'ContentType': 'image/png'}

    def delete_object(self, **kwargs):
        self.deleted.append(kwargs['Key'])
        self.objects.pop(kwargs['Key'], None)


class FakeUpload:
    content_type = 'image/png'
    filename = 'source.png'

    async def read(self):
        return b'png original content'


class FakeForm(dict):
    def getlist(self, key):
        return self[key]


class FakeRequest:
    async def form(self):
        return FakeForm(screenshots=[FakeUpload()])


class FakeDB:
    def __init__(self, fail=False):
        self.rows = []
        self.fail = fail
        self.rolled_back = False

    def add(self, row):
        self.rows.append(row)

    def commit(self):
        if self.fail:
            raise RuntimeError('database offline')

    def rollback(self):
        self.rolled_back = True


class StoredImageTests(unittest.TestCase):
    def setUp(self):
        self.r2 = FakeR2()
        self.env = patch.dict(os.environ, {'MEDIA_STORAGE_BACKEND': 'r2', 'R2_BUCKET': 'private', 'R2_PREFIX': 'golf-coach'})
        self.client = patch('app.services.media_storage.r2_client', return_value=self.r2)
        self.env.start()
        self.client.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.client.stop)

    def test_new_database_value_is_reference_and_remains_readable_when_writes_go_local(self):
        data = b'full image content' * 1000
        stored = images.store_image_data(data, 'image/png', 'session_screenshots')
        self.assertLess(len(stored), 200)
        self.assertTrue(stored.startswith(images.MARKER))
        self.assertEqual(images.resolve_image_data(stored), data)
        with patch.dict(os.environ, {'MEDIA_STORAGE_BACKEND': 'local'}):
            self.assertEqual(images.resolve_image_data(stored), data)
        self.assertEqual(len(self.r2.objects), 1)

    def test_legacy_database_values_and_local_default_are_unchanged(self):
        data = b'legacy binary image'
        self.assertEqual(images.resolve_image_data(data), data)
        with patch.dict(os.environ, {'MEDIA_STORAGE_BACKEND': 'local'}):
            self.assertEqual(images.store_image_data(data, 'image/png', 'session_screenshots'), data)
        self.assertEqual(self.r2.objects, {})

    def test_invalid_marker_cannot_access_other_categories_or_paths(self):
        for record in [
            {'category': 'arbitrary', 'name': 'r2__' + 'a' * 32 + '.png'},
            {'category': 'session_screenshots', 'name': '../secret.png'},
            {'category': 'session_screenshots', 'name': 'https://evil.example/image'},
            {'category': 'session_screenshots', 'name': ['bad']},
        ]:
            with self.subTest(record=record), self.assertRaises(HTTPException) as error:
                images.resolve_image_data(images.MARKER + json.dumps(record).encode())
            self.assertEqual(error.exception.status_code, 503)

    def test_screenshot_upload_persists_small_reference_instead_of_media_bytes(self):
        db = FakeDB()
        with patch.object(sessions, 'require_session'):
            response = asyncio.run(sessions.session_screenshot_upload('session-1', FakeRequest(), db))
        self.assertEqual(response.status_code, 303)
        self.assertEqual(len(db.rows), 1)
        self.assertTrue(db.rows[0].image_data.startswith(images.MARKER))
        self.assertEqual(images.resolve_image_data(db.rows[0].image_data), b'png original content')

    def test_database_failure_removes_new_r2_upload(self):
        db = FakeDB(fail=True)
        with patch.object(sessions, 'require_session'), self.assertRaises(RuntimeError):
            asyncio.run(sessions.session_screenshot_upload('session-1', FakeRequest(), db))
        self.assertTrue(db.rolled_back)
        self.assertEqual(self.r2.objects, {})
        self.assertEqual(len(self.r2.deleted), 1)

    def test_p_sheet_upload_uses_its_own_private_category(self):
        class SheetRequest:
            async def form(self):
                return {'image': FakeUpload(), 'title': 'P4'}

        db = FakeDB()
        with patch.object(sessions, 'require_session'):
            response = asyncio.run(sessions.p_sheet_upload('session-1', SheetRequest(), db))
        self.assertEqual(response.status_code, 303)
        category, _ = images.image_reference(db.rows[0].image_data)
        self.assertEqual(category, 'p_position_sheets')
        self.assertEqual(images.resolve_image_data(db.rows[0].image_data), b'png original content')

    def test_private_response_serves_media_instead_of_reference(self):
        data = b'full image'
        stored = images.store_image_data(data, 'image/png', 'session_screenshots')
        request = Request({'type': 'http', 'method': 'GET', 'headers': []})
        response = images.image_response(request, stored, 'image/png')

        async def consume():
            return b''.join([part async for part in response.body_iterator])

        self.assertEqual(asyncio.run(consume()), data)
        self.assertEqual(response.headers['cache-control'], 'private, no-store')

    def test_ai_consumers_encode_resolved_bytes(self):
        data = b'actual image content'
        stored = images.store_image_data(data, 'image/png', 'session_screenshots')
        output = {'student_notes': 'student', 'coach_notes': 'coach'}
        response = json.dumps({'output': [{'content': [{'type': 'output_text', 'text': json.dumps(output)}]}]}).encode()
        requests = []

        def reply(request, **kwargs):
            requests.append(json.loads(request.data))
            return io.BytesIO(response)

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}), patch('urllib.request.urlopen', side_effect=reply):
            coach_assistant_ai.generate_screenshot_lesson(student_name='Test', session_context='', screenshots=[{
                'image_data': stored, 'content_type': 'image/png', 'filename': 'source.png'}])
            p_sheet_analyzer.analyze([{'image_data': stored, 'content_type': 'image/png', 'title': 'P4'}])
        expected = 'data:image/png;base64,' + base64.b64encode(data).decode()
        for payload in requests:
            entries = payload['input'][-1]['content']
            self.assertEqual(next(item['image_url'] for item in entries if item['type'] == 'input_image'), expected)


if __name__ == '__main__':
    unittest.main()
