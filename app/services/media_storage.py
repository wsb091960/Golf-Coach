"""Private media storage. R2 is opt-in; legacy local files remain readable.

Keys are category/basename under R2_PREFIX. Routes authorize the student/session
before calling response(); objects are never published or exposed by bucket URL.
"""
from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import tempfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse


def r2_enabled() -> bool:
    backend = os.getenv('MEDIA_STORAGE_BACKEND', 'local').strip().lower()
    if backend not in {'local', 'r2'}:
        raise RuntimeError('MEDIA_STORAGE_BACKEND must be local or r2')
    return backend == 'r2'


@lru_cache(maxsize=1)
def r2_client():
    import boto3
    from botocore.config import Config
    required = ['R2_ACCOUNT_ID', 'R2_BUCKET', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY']
    if any(not os.getenv(key, '').strip() for key in required):
        raise RuntimeError('R2 configuration is incomplete; media storage was not changed')
    account = os.environ['R2_ACCOUNT_ID'].strip()
    if not re.fullmatch(r'[a-fA-F0-9]{32}', account):
        raise RuntimeError('Invalid R2 account ID')
    return boto3.client('s3',
        endpoint_url=f'https://{account}.r2.cloudflarestorage.com',
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
        region_name='auto',
        config=Config(signature_version='s3v4', connect_timeout=10, read_timeout=60,
                      request_checksum_calculation='when_required',
                      response_checksum_validation='when_required',
                      retries={'max_attempts': 3, 'mode': 'standard'}))


def _not_found(exc: Exception) -> bool:
    response = getattr(exc, 'response', {})
    return str(response.get('Error', {}).get('Code', '')) in {'404', 'NoSuchKey', 'NotFound'}


class MediaStore:
    def __init__(self, category: str, legacy_root: Path, client=None):
        if not re.fullmatch(r'[a-z_]+', category):
            raise ValueError('Invalid media category')
        self.category = category
        self.root = Path(legacy_root)
        self._client = client

    @property
    def client(self):
        return self._client if self._client is not None else r2_client()

    def key(self, name: str) -> str:
        self.local_path(name)  # validate before using either backend
        prefix = os.getenv('R2_PREFIX', 'golf-coach').strip('/')
        if any(p in {'.', '..'} for p in prefix.split('/')):
            raise ValueError('Invalid R2 prefix')
        return '/'.join(part for part in [prefix, self.category, name] if part)

    def local_path(self, name: str) -> Path:
        if not name or name in {'.', '..'} or '/' in name or '\\' in name or '\x00' in name:
            raise ValueError('Invalid media filename')
        path = self.root / name
        if path.resolve().parent != self.root.resolve():
            raise ValueError('Invalid media path')
        return path

    @property
    def bucket(self):
        return os.environ['R2_BUCKET']

    def save_bytes(self, name: str, data: bytes, content_type: str | None = None):
        path = self.local_path(name)
        content_type = content_type or mimetypes.guess_type(name)[0] or 'application/octet-stream'
        if r2_enabled():
            self.client.put_object(Bucket=self.bucket, Key=self.key(name), Body=data,
                ContentType=content_type, Metadata={'sha256': hashlib.sha256(data).hexdigest()})
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Never let readers observe half a local upload.
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                output.write(data)
            try:
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)

    def save_file(self, name: str, source: Path, content_type: str | None = None):
        self.local_path(name)
        if not r2_enabled():
            return  # caller already assembled the file in the legacy root
        digest = hashlib.sha256()
        with source.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        self.client.upload_file(str(source), self.bucket, self.key(name), ExtraArgs={
            'ContentType': content_type or mimetypes.guess_type(name)[0] or 'application/octet-stream',
            'Metadata': {'sha256': digest.hexdigest()},
        })
        metadata = self.client.head_object(Bucket=self.bucket, Key=self.key(name))
        if (metadata.get('ContentLength') != source.stat().st_size
                or metadata.get('Metadata', {}).get('sha256') != digest.hexdigest()):
            raise RuntimeError('Uploaded media verification failed; local source retained')
        # Verified upload succeeds before temporary assembled media is removed.
        source.unlink()

    def read_bytes(self, name: str) -> bytes:
        """Read image bytes for analysis; video routes use response() streaming."""
        path = self.local_path(name)
        if r2_enabled() or name.startswith('r2__'):
            try:
                remote = self.client.get_object(Bucket=self.bucket, Key=self.key(name))
            except Exception as exc:
                if not _not_found(exc):
                    raise HTTPException(503, 'Media storage is temporarily unavailable') from exc
            else:
                body = remote['Body']
                try:
                    return body.read()
                finally:
                    body.close()
        if not path.is_file():
            raise HTTPException(404, 'Media file is missing')
        return path.read_bytes()

    def exists(self, name: str) -> bool:
        path = self.local_path(name)
        if r2_enabled() or name.startswith('r2__'):
            try:
                self.client.head_object(Bucket=self.bucket, Key=self.key(name))
                return True
            except Exception as exc:
                if not _not_found(exc):
                    raise HTTPException(503, 'Media storage is temporarily unavailable') from exc
        return path.is_file()

    def delete(self, name: str):
        path = self.local_path(name)
        if r2_enabled() or name.startswith('r2__'):
            self.client.delete_object(Bucket=self.bucket, Key=self.key(name))
        path.unlink(missing_ok=True)

    def response(self, request: Request, name: str, content_type: str | None = None,
                 filename: str | None = None, download: bool = False):
        path = self.local_path(name)
        if not (r2_enabled() or name.startswith('r2__')):
            if not path.is_file():
                raise HTTPException(404, 'Media file is missing')
            return FileResponse(path, media_type=content_type, filename=filename,
                                content_disposition_type='attachment' if download else 'inline')
        try:
            metadata = self.client.head_object(Bucket=self.bucket, Key=self.key(name))
        except Exception as exc:
            if _not_found(exc):
                if path.is_file():
                    return FileResponse(path, media_type=content_type, filename=filename,
                                        content_disposition_type='attachment' if download else 'inline')
                raise HTTPException(404, 'Media file is missing') from exc
            raise HTTPException(503, 'Media storage is temporarily unavailable') from exc
        size = int(metadata['ContentLength'])
        range_value = request.headers.get('range')
        params = {'Bucket': self.bucket, 'Key': self.key(name)}
        status = 200
        headers = {'Accept-Ranges': 'bytes', 'Cache-Control': 'private, no-store'}
        if range_value:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', range_value)
            if not match or not any(match.groups()) or size == 0:
                raise HTTPException(416, 'Invalid media range', headers={'Content-Range': f'bytes */{size}'})
            first, last = match.groups()
            if first:
                start, end = int(first), min(int(last) if last else size - 1, size - 1)
            else:
                start, end = max(0, size - int(last)), size - 1
            if start > end or start >= size:
                raise HTTPException(416, 'Invalid media range', headers={'Content-Range': f'bytes */{size}'})
            params['Range'] = f'bytes={start}-{end}'
            headers['Content-Range'] = f'bytes {start}-{end}/{size}'
            headers['Content-Length'] = str(end - start + 1)
            status = 206
        else:
            headers['Content-Length'] = str(size)
        if filename:
            disposition = 'attachment' if download else 'inline'
            headers['Content-Disposition'] = f"{disposition}; filename*=UTF-8''{quote(filename, safe='')}"
        try:
            remote = self.client.get_object(**params)
        except Exception as exc:
            raise HTTPException(503, 'Media storage is temporarily unavailable') from exc
        body = remote['Body']
        def blocks():
            try:
                yield from iter(lambda: body.read(256 * 1024), b'')
            finally:
                body.close()
        return StreamingResponse(blocks(), status_code=status, headers=headers,
            media_type=content_type or metadata.get('ContentType', 'application/octet-stream'))
