import hashlib
import io
import json
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from app.services.media_storage import MediaStore
from scripts.migrate_media_to_r2 import copy_verified, main


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.corrupt = False

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({'Error': {'Code': '404'}}, 'HeadObject')
        body, extra = self.objects[Key]
        return {'ContentLength': len(body), 'Metadata': extra['Metadata']}

    def upload_file(self, path, bucket, key, ExtraArgs):
        self.objects[key] = (Path(path).read_bytes(), ExtraArgs)

    def get_object(self, Bucket, Key):
        data = self.objects[Key][0]
        return {'Body': io.BytesIO(b'corrupt' if self.corrupt else data)}


def test_verified_copy_and_retry_preserve_original(tmp_path, monkeypatch):
    monkeypatch.setenv('R2_BUCKET', 'test')
    path = tmp_path / 'swing.mp4'
    path.write_bytes(b'recorded swing')
    client = FakeS3()
    store = MediaStore('session_videos', tmp_path, client=client)
    result = copy_verified(store, path)
    assert result['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert copy_verified(store, path) == result
    assert path.read_bytes() == b'recorded swing'


def test_conflict_and_corrupt_download_do_not_remove_original(tmp_path, monkeypatch):
    monkeypatch.setenv('R2_BUCKET', 'test')
    path = tmp_path / 'swing.mp4'
    path.write_bytes(b'first')
    client = FakeS3()
    store = MediaStore('session_videos', tmp_path, client=client)
    copy_verified(store, path)
    path.write_bytes(b'second')
    with pytest.raises(RuntimeError, match='conflict'):
        copy_verified(store, path)
    assert path.read_bytes() == b'second'
    path.write_bytes(b'first')
    client.corrupt = True
    with pytest.raises(RuntimeError, match='verification failed'):
        copy_verified(store, path)
    assert path.read_bytes() == b'first'


def test_inventory_needs_no_credentials_or_client(tmp_path, monkeypatch):
    for key in ('R2_BUCKET', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_ACCOUNT_ID'):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / 'media'
    (root / 'onform_screenshots').mkdir(parents=True)
    (root / 'onform_screenshots' / 'p7.png').write_bytes(b'image')
    manifest = tmp_path / 'inventory.json'
    assert main(['--media-root', str(root), '--manifest', str(manifest)]) == 0
    data = json.loads(manifest.read_text())
    assert data['files'][0]['status'] == 'inventory_only'
    assert data['files'][0]['size_bytes'] == 5
