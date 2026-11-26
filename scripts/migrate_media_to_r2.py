"""Copy legacy filesystem media to R2 without deleting or rewriting originals.

Run on the host containing the real media, with app writes paused. Default is
inventory only; --apply uploads and downloads every object to verify its bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.media_storage import MediaStore, _not_found, r2_client


CATEGORIES = ('session_videos', 'onform_screenshots')


def checksum(stream):
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(block)
    return digest.hexdigest()


def copy_verified(store, path):
    """Refuse a conflicting destination; verify downloaded bytes after upload."""
    with path.open('rb') as source:
        digest = checksum(source)
    size = path.stat().st_size
    key = store.key(path.name)
    client = store.client
    try:
        existing = client.head_object(Bucket=store.bucket, Key=key)
    except Exception as exc:
        if not _not_found(exc):
            raise
        existing = None
    if existing is not None:
        if (int(existing['ContentLength']) != size
                or existing.get('Metadata', {}).get('sha256') != digest):
            raise RuntimeError(f'Destination conflict for {store.category}/{path.name}; original retained')
    else:
        client.upload_file(str(path), store.bucket, key, ExtraArgs={
            'ContentType': mimetypes.guess_type(path.name)[0] or 'application/octet-stream',
            'Metadata': {'sha256': digest},
        })
    response = client.get_object(Bucket=store.bucket, Key=key)
    body = response['Body']
    try:
        remote_digest = checksum(body)
    finally:
        body.close()
    if remote_digest != digest:
        raise RuntimeError(f'Content verification failed for {store.category}/{path.name}; original retained')
    return {'category': store.category, 'filename': path.name, 'object_key': key,
            'size_bytes': size, 'sha256': digest, 'status': 'verified'}


def save_manifest(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps({'updated_at': datetime.now(timezone.utc).isoformat(),
                                    'originals_retained': True, 'files': records}, indent=2) + '\n')
    temporary.replace(path)


def main(argv=None, client=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--media-root', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'app' / 'media')
    parser.add_argument('--manifest', required=True, type=Path,
                        help='Private manifest path outside the Git repository')
    parser.add_argument('--apply', action='store_true', help='Upload and verify; default only inventories')
    args = parser.parse_args(argv)
    if args.manifest.resolve().is_relative_to(args.media_root.resolve()):
        parser.error('Keep the manifest outside the media root so it cannot overwrite media')
    if args.manifest.is_symlink():
        parser.error('The manifest must not be a symbolic link')
    if args.apply:
        client = client or r2_client()
    records = []
    for category in CATEGORIES:
        root = args.media_root / category
        if not root.is_dir():
            continue
        store = MediaStore(category, root, client=client)
        for path in sorted(root.iterdir()):
            if path.name.startswith('.') or not path.is_file():
                continue
            if path.is_symlink():
                raise RuntimeError(f'Refusing symbolic link: {category}/{path.name}')
            kind = mimetypes.guess_type(path.name)[0] or ''
            if not kind.startswith(('image/', 'audio/', 'video/')):
                continue
            if args.apply:
                entry = copy_verified(store, path)
            else:
                entry = {'category': category, 'filename': path.name,
                         'size_bytes': path.stat().st_size, 'object_key': store.key(path.name),
                         'status': 'inventory_only'}
            records.append(entry)
            save_manifest(args.manifest, records)
    save_manifest(args.manifest, records)
    print(json.dumps({'mode': 'copy_and_verify' if args.apply else 'inventory_only',
                      'files': len(records), 'bytes': sum(r['size_bytes'] for r in records),
                      'originals_retained': True}))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Do not print SDK exceptions, signed URLs, or credentials.
        print(f'Migration stopped ({type(exc).__name__}); originals retained.', file=sys.stderr)
        raise SystemExit(1)
