"""Explicit pre/post-redeploy check of paired private media and database storage.

Initialize once, record the returned marker, then verify that exact marker after
a restart/redeploy or backup restore. The marker contains no student data and
does not authorize access. Verification never repairs or replaces missing data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import engine, SessionLocal
from app.online_instruction import OnlineStorageProbe
from app.routers.online_instruction import media_root


def check(initialize=False, expected_marker=None):
    root = media_root()
    path = root / '.wsbco-online-storage-check.json'
    if initialize:
        if expected_marker:
            raise ValueError('Initialization does not accept an existing marker.')
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        OnlineStorageProbe.__table__.create(engine, checkfirst=True)
        with SessionLocal() as db:
            if path.exists() or db.get(OnlineStorageProbe, 'pilot'):
                raise ValueError('A probe already exists. Verify it; do not initialize again.')
            marker = secrets.token_hex(16)
            content = json.dumps({'marker': marker, 'purpose': 'online-instruction-storage-check'}).encode()
            with path.open('xb') as stream:
                os.chmod(path, 0o600)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                db.add(OnlineStorageProbe(id='pilot', marker_hash=hashlib.sha256(content).hexdigest()))
                db.commit()
            except Exception:
                path.unlink(missing_ok=True)
                raise
        return {'result': 'initialized', 'marker': marker,
                'next': 'Record this marker. Verify it after restart/redeploy or restore.'}
    if not expected_marker:
        raise ValueError('Verification requires the exact --expected-marker from initialization.')
    if not path.is_file():
        raise ValueError('Media probe is missing. Do not initialize a replacement to pass this check.')
    content = path.read_bytes()
    marker = json.loads(content).get('marker')
    if marker != expected_marker:
        raise ValueError('The media marker does not match the recorded marker.')
    with SessionLocal() as db:
        row = db.get(OnlineStorageProbe, 'pilot')
        if not row or row.marker_hash != hashlib.sha256(content).hexdigest():
            raise ValueError('The database probe is missing or does not match the media probe.')
    return {'result': 'verified', 'marker': marker, 'free_bytes': shutil.disk_usage(root).free}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initialize', action='store_true')
    parser.add_argument('--expected-marker')
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.initialize, args.expected_marker)))
    except Exception as error:
        # Do not print SQLAlchemy URLs/tracebacks, which can contain credentials.
        message = str(error) if isinstance(error, ValueError) else 'Storage check failed. Check private storage and database configuration.'
        print(json.dumps({'result': 'failed', 'message': message}))
        sys.exit(1)
