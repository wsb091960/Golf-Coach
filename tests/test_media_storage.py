import asyncio
import hashlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request
from app.services.media_storage import MediaStore, r2_enabled


class Missing(Exception):
    response = {'Error': {'Code': 'NoSuchKey'}}


class FakeS3:
    def __init__(self):
        self.items = {}
        self.ranges = []
    def put_object(self, **kw):
        self.items[kw['Key']] = dict(Body=kw['Body'], ContentType=kw['ContentType'], Metadata=kw['Metadata'])
    def upload_file(self, path, bucket, key, ExtraArgs):
        self.put_object(Bucket=bucket, Key=key, Body=Path(path).read_bytes(), **ExtraArgs)
    def head_object(self, Bucket, Key):
        if Key not in self.items:
            raise Missing()
        item = self.items[Key]
        return dict(ContentLength=len(item['Body']), ContentType=item['ContentType'], Metadata=item['Metadata'])
    def get_object(self, Bucket, Key, Range=None):
        if Key not in self.items:
            raise Missing()
        data = self.items[Key]['Body']
        if Range:
            self.ranges.append(Range)
            first, last = Range[6:].split('-')
            data = data[int(first):int(last)+1]
        return {'Body': io.BytesIO(data)}
    def delete_object(self, Bucket, Key):
        self.items.pop(Key, None)


def request(range_value=None):
    headers = [(b'range', range_value.encode())] if range_value else []
    return Request({'type': 'http', 'method': 'GET', 'headers': headers})


class MediaStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.client = FakeS3()
        self.env = patch.dict(os.environ, {'MEDIA_STORAGE_BACKEND': 'r2', 'R2_BUCKET': 'private', 'R2_PREFIX': 'golf'})
        self.env.start()
        self.store = MediaStore('session_videos', self.root, self.client)
    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()
    def test_remote_upload_and_checksum_without_local_copy(self):
        self.store.save_bytes('abc.mp4', b'0123456789', 'video/mp4')
        self.assertFalse((self.root/'abc.mp4').exists())
        self.assertTrue(self.store.exists('abc.mp4'))
        self.assertEqual(self.store.read_bytes('abc.mp4'), b'0123456789')
        self.assertEqual(self.client.items['golf/session_videos/abc.mp4']['Metadata']['sha256'], hashlib.sha256(b'0123456789').hexdigest())
    def test_local_backend_round_trip_and_filename_validation(self):
        with patch.dict(os.environ, {'MEDIA_STORAGE_BACKEND': 'local'}):
            self.store.save_bytes('abc.png', b'png')
            self.assertEqual(self.store.read_bytes('abc.png'), b'png')
        for name in ['../secret', '/tmp/secret', 'a/b', 'a\\b', '.', '..', '']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.store.local_path(name)
    def test_legacy_local_read_after_enabling_r2(self):
        (self.root/'legacy.mp4').write_bytes(b'old-video')
        self.assertTrue(self.store.exists('legacy.mp4'))
        self.assertEqual(self.store.read_bytes('legacy.mp4'), b'old-video')
        self.assertEqual(self.store.response(request(), 'legacy.mp4').path, self.root/'legacy.mp4')
    def test_marked_reference_survives_local_write_backend(self):
        self.store.save_bytes('r2__image.png', b'png')
        with patch.dict(os.environ, {'MEDIA_STORAGE_BACKEND': 'local'}):
            self.assertEqual(self.store.read_bytes('r2__image.png'), b'png')
            self.store.delete('r2__image.png')
        self.assertFalse(self.store.exists('r2__image.png'))
    def test_response_range_suffix_and_bad_ranges(self):
        self.store.save_bytes('abc.mp4', b'0123456789', 'video/mp4')
        for value, expected in [('bytes=2-5','bytes 2-5/10'), ('bytes=-3','bytes 7-9/10'), ('bytes=8-99','bytes 8-9/10')]:
            response = self.store.response(request(value), 'abc.mp4', 'video/mp4')
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response.headers['content-range'], expected)
        for value in ['bytes=20-', 'bytes=5-2', 'bytes=-0', 'bytes=0-1,3-5', 'foo']:
            with self.subTest(value=value), self.assertRaises(HTTPException) as ctx:
                self.store.response(request(value), 'abc.mp4')
            self.assertEqual(ctx.exception.status_code, 416)
    def test_streamed_range_body_matches_headers_and_closes_connection(self):
        self.store.save_bytes('video.mp4', b'abcdefghij', 'video/mp4')
        remote_body = io.BytesIO(b'def')
        with patch.object(self.client, 'get_object', return_value={'Body': remote_body}) as fetch:
            response = self.store.response(request('bytes=3-5'), 'video.mp4')
            async def collect():
                return b''.join([chunk async for chunk in response.body_iterator])
            self.assertEqual(asyncio.run(collect()), b'def')
            self.assertEqual(response.headers['content-length'], '3')
            self.assertTrue(remote_body.closed)
            self.assertEqual(fetch.call_args.kwargs['Range'], 'bytes=3-5')

    def test_real_sdk_upload_parameters_pass_stub_validation(self):
        import boto3
        from botocore.stub import Stubber
        client = boto3.client('s3', region_name='auto',
            endpoint_url='https://1234567890abcdef1234567890abcdef.r2.cloudflarestorage.com',
            aws_access_key_id='test', aws_secret_access_key='test')
        store = MediaStore('session_videos', self.root, client)
        data = b'abc'
        expected = {'Bucket': 'private', 'Key': 'golf/session_videos/video.mp4',
            'Body': data, 'ContentType': 'video/mp4',
            'Metadata': {'sha256': hashlib.sha256(data).hexdigest()}}
        with Stubber(client) as stub:
            stub.add_response('put_object', {'ETag': 'example'}, expected)
            store.save_bytes('video.mp4', data, 'video/mp4')
            stub.assert_no_pending_responses()

    def test_verified_streaming_file_upload_removes_only_temporary_copy(self):
        source = self.root/'swing.mp4'
        source.write_bytes(b'abc')
        self.store.save_file('swing.mp4', source, 'video/mp4')
        self.assertFalse(source.exists())
        self.assertEqual(self.store.read_bytes('swing.mp4'), b'abc')
    def test_failed_upload_preserves_source(self):
        source = self.root/'swing.mp4'
        source.write_bytes(b'abc')
        with patch.object(self.client, 'upload_file', side_effect=OSError('offline')):
            with self.assertRaises(OSError):
                self.store.save_file('swing.mp4', source, 'video/mp4')
        self.assertEqual(source.read_bytes(), b'abc')
    def test_storage_error_does_not_silently_fall_back_to_stale_copy(self):
        (self.root/'abc.mp4').write_bytes(b'stale')
        with patch.object(self.client, 'head_object', side_effect=OSError('offline')):
            with self.assertRaises(HTTPException) as ctx:
                self.store.response(request(), 'abc.mp4')
            self.assertEqual(ctx.exception.status_code, 503)
    def test_unknown_backend_fails_closed(self):
        with patch.dict(os.environ, {'MEDIA_STORAGE_BACKEND': 'typo'}):
            with self.assertRaises(RuntimeError): r2_enabled()


if __name__ == '__main__':
    unittest.main()
