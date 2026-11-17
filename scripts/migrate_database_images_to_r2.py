"""Inventory or migrate existing SQLite screenshot/P-sheet image blobs to R2.

Dry-run is the default. Apply requires a new database backup and JSONL journal.
Every object is downloaded and SHA-256 checked before a conditional row update.
The backup retains originals; this script never vacuums SQLite or rewrites Git.
Run from the repository root: python -m scripts.migrate_database_images_to_r2 ...
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.media_storage import r2_enabled
from app.services.stored_images import (
    IMAGE_EXTENSIONS, MARKER, image_reference, resolve_image_data, store_image_data,
)

TABLE_CATEGORIES = {
    "session_screenshots": "session_screenshots",
    "session_p_sheets": "p_position_sheets",
}
REQUIRED_COLUMNS = {"id", "session_id", "original_filename", "content_type", "image_data"}


def _readonly(path: Path):
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)


def _new_private_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)


def _backup(database: Path, destination: Path):
    if database == destination:
        raise ValueError("Backup must use a different path")
    os.close(_new_private_file(destination))
    with _readonly(database) as source, sqlite3.connect(destination) as target:
        source.backup(target)
        if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Database backup failed its integrity check")


def _tables(connection, selected):
    available = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    result = []
    for table in selected:
        if table not in TABLE_CATEGORIES:
            raise ValueError("Unsupported image table")
        if table not in available:
            continue
        columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
        if not REQUIRED_COLUMNS.issubset(columns):
            raise ValueError(f"Image table {table} does not match the expected schema")
        result.append(table)
    return result


def migrate(database: Path, *, apply=False, backup_path=None, manifest_path=None,
            tables=None, store=None, resolve=None):
    """Return counts; stop on first failed object, preserving that original row.

    Snapshot candidates come from the verified backup during apply. A later
    upload or concurrently modified row is never overwritten. Completed rows
    are skipped automatically on the next run with a fresh backup/journal.
    """
    database = Path(database).resolve(strict=True)
    if not database.is_file():
        raise ValueError("Database must be an existing file")
    selected = tuple(tables or TABLE_CATEGORIES)
    if not selected or any(table not in TABLE_CATEGORIES for table in selected):
        raise ValueError("Unsupported image table")
    if apply and (backup_path is None or manifest_path is None):
        raise ValueError("Apply requires a new --backup and --manifest path")
    if apply and not r2_enabled():
        raise ValueError("Set MEDIA_STORAGE_BACKEND=r2 before applying the migration")
    store = store or store_image_data
    resolve = resolve or resolve_image_data
    counts = {key: 0 for key in (
        "scanned", "eligible", "source_bytes", "already_external", "migrated",
        "changed_skipped", "unsupported", "empty", "invalid_reference", "failed",
    )}
    counts["dry_run"] = not apply
    journal = None
    snapshot = None
    live = None

    def record(status, **details):
        if journal is not None:
            journal.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(),
                                      "status": status, **details}) + "\n")
            journal.flush()
            os.fsync(journal.fileno())

    try:
        if manifest_path is not None:
            manifest_path = Path(manifest_path).resolve()
            if manifest_path == database:
                raise ValueError("Manifest must use a different path")
            journal = os.fdopen(_new_private_file(manifest_path), "w", encoding="utf-8")
        if apply:
            backup_path = Path(backup_path).resolve()
            if manifest_path == backup_path:
                raise ValueError("Backup and manifest must use different paths")
            _backup(database, backup_path)
            snapshot = _readonly(backup_path)
            live = sqlite3.connect(database, timeout=10)
        else:
            snapshot = _readonly(database)
        selected = _tables(snapshot, selected)
        record("started", dry_run=not apply, tables=selected)
        stop = False
        for table in selected:
            if stop:
                break
            category = TABLE_CATEGORIES[table]
            cursor = snapshot.execute(
                f'SELECT id, session_id, original_filename, content_type, image_data FROM "{table}" ORDER BY id')
            for row_id, session_id, filename, content_type, value in cursor:
                counts["scanned"] += 1
                identity = {"table": table, "row_id": str(row_id), "session_id": str(session_id)}
                data = bytes(value or b"")
                if not data:
                    counts["empty"] += 1
                    record("empty_skipped", **identity)
                    continue
                if data.startswith(MARKER):
                    try:
                        image_reference(data)
                    except Exception:
                        counts["invalid_reference"] += 1
                        record("invalid_reference", **identity)
                    else:
                        counts["already_external"] += 1
                        record("already_external", **identity)
                    continue
                if content_type not in IMAGE_EXTENSIONS:
                    counts["unsupported"] += 1
                    record("unsupported_type", content_type=content_type, **identity)
                    continue
                counts["eligible"] += 1
                counts["source_bytes"] += len(data)
                digest = hashlib.sha256(data).hexdigest()
                details = {**identity, "source_bytes": len(data), "source_sha256": digest}
                if not apply:
                    record("eligible", **details)
                    continue
                reference = None
                try:
                    current = live.execute(f'SELECT image_data FROM "{table}" WHERE id=?', (row_id,)).fetchone()
                    if current is None or current[0] != data:
                        counts["changed_skipped"] += 1
                        record("changed_skipped", **details)
                        continue
                    reference = store(data, content_type, category)
                    parsed = image_reference(reference)
                    if parsed is None or parsed[0] != category:
                        raise ValueError("Storage did not return a valid external image reference")
                    remote = resolve(reference)
                    if len(remote) != len(data) or hashlib.sha256(remote).hexdigest() != digest:
                        raise ValueError("The downloaded object did not match the original image")
                    object_details = {"object_category": parsed[0], "object_name": parsed[1]}
                    record("verified_pending_commit", **details, **object_details)
                    # One transaction per row. The value comparison also guards
                    # edits/deletion during the potentially slow object upload.
                    with live:
                        updated = live.execute(
                            f'UPDATE "{table}" SET image_data=? WHERE id=? AND image_data=?',
                            (reference, row_id, data)).rowcount
                    if updated:
                        counts["migrated"] += 1
                        record("committed", **details, **object_details)
                    else:
                        counts["changed_skipped"] += 1
                        record("changed_skipped_after_upload", **details, **object_details)
                except Exception as error:
                    if live is not None:
                        live.rollback()
                    counts["failed"] += 1
                    # Keep the new object for recoverable reconciliation. The
                    # live source row and backup still hold the original bytes.
                    extra = {}
                    if reference is not None:
                        try:
                            parsed = image_reference(reference)
                            if parsed:
                                extra = {"object_category": parsed[0], "object_name": parsed[1]}
                        except Exception:
                            pass
                    record("failed", error_type=type(error).__name__, **details, **extra)
                    stop = True
                    break
        record("finished", **counts)
        return counts
    finally:
        for resource in (snapshot, live, journal):
            if resource is not None:
                resource.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--table", choices=tuple(TABLE_CATEGORIES), action="append",
                        help="Optional table filter; defaults to screenshots and P-sheets")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", type=Path, help="New private SQLite backup path, required for apply")
    parser.add_argument("--manifest", type=Path, help="New private JSONL progress journal; required for apply")
    args = parser.parse_args()
    try:
        counts = migrate(args.database, apply=args.apply, backup_path=args.backup,
                         manifest_path=args.manifest, tables=args.table)
    except Exception as error:
        parser.exit(2, f"Migration stopped ({type(error).__name__}). Check paths, configuration, and database access; retain any created backup and inspect the journal before retrying.\n")
    print(json.dumps(counts, indent=2))
    return 2 if counts["failed"] or counts["invalid_reference"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
