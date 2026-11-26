import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from app.services.stored_images import MARKER
from scripts.migrate_database_images_to_r2 import migrate


class DatabaseImageMigrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.database = self.root / 'images.sqlite'
        self.backup = self.root / 'backup.sqlite'
        self.manifest = self.root / 'migration.jsonl'
        self.data = b'original PNG bytes' * 200
        self.objects = {}
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE session_screenshots (id TEXT PRIMARY KEY, session_id TEXT, original_filename TEXT, content_type TEXT, image_data BLOB)')
            db.execute('INSERT INTO session_screenshots VALUES (?, ?, ?, ?, ?)',
                       ('image-1', 'session-1', 'original.png', 'image/png', self.data))
        self.env = patch.dict(os.environ, {'MEDIA_STORAGE_BACKEND': 'r2'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def store(self, data, content_type, category):
        name = 'r2__' + f'{len(self.objects) + 1:032x}' + '.png'
        self.objects[name] = data
        return MARKER + json.dumps({'category': category, 'name': name}).encode()

    def resolve(self, reference):
        return self.objects[json.loads(reference[len(MARKER):])['name']]

    def read_image(self, path=None):
        with sqlite3.connect(path or self.database) as db:
            return db.execute('SELECT image_data FROM session_screenshots WHERE id=?', ('image-1',)).fetchone()[0]

    def apply(self, **kwargs):
        return migrate(self.database, apply=True, backup_path=self.backup, manifest_path=self.manifest,
                       store=self.store, resolve=kwargs.pop('resolve', self.resolve), **kwargs)

    def test_dry_run_never_uploads_or_changes_database(self):
        before = self.database.read_bytes()
        result = migrate(self.database, store=self.store, resolve=self.resolve)
        self.assertTrue(result['dry_run'])
        self.assertEqual(result['eligible'], 1)
        self.assertEqual(result['source_bytes'], len(self.data))
        self.assertEqual(self.objects, {})
        self.assertEqual(self.database.read_bytes(), before)
        self.assertFalse(self.backup.exists())

    def test_success_keeps_original_backup_and_records_verified_commit(self):
        result = self.apply()
        self.assertEqual(result['migrated'], 1)
        self.assertEqual(result['failed'], 0)
        reference = self.read_image()
        self.assertTrue(reference.startswith(MARKER))
        self.assertEqual(self.resolve(reference), self.data)
        self.assertEqual(self.read_image(self.backup), self.data)
        records = [json.loads(line) for line in self.manifest.read_text().splitlines()]
        statuses = [record['status'] for record in records]
        self.assertLess(statuses.index('verified_pending_commit'), statuses.index('committed'))
        self.assertEqual(self.backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.manifest.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('original PNG bytes', self.manifest.read_text())

    def test_corrupt_download_leaves_source_and_backup_unchanged(self):
        result = self.apply(resolve=lambda value: b'corrupt')
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['migrated'], 0)
        self.assertEqual(self.read_image(), self.data)
        self.assertEqual(self.read_image(self.backup), self.data)
        self.assertIn('"status": "failed"', self.manifest.read_text())

    def test_database_abort_rolls_back_row_without_losing_original(self):
        with sqlite3.connect(self.database) as db:
            db.execute("CREATE TRIGGER reject_update BEFORE UPDATE ON session_screenshots BEGIN SELECT RAISE(ABORT, 'blocked'); END")
        result = self.apply()
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['migrated'], 0)
        self.assertEqual(self.read_image(), self.data)
        self.assertEqual(self.read_image(self.backup), self.data)

    def test_concurrent_edit_during_upload_is_preserved(self):
        def store_and_edit(data, content_type, category):
            reference = self.store(data, content_type, category)
            with sqlite3.connect(self.database) as db:
                db.execute('UPDATE session_screenshots SET image_data=? WHERE id=?', (b'new image bytes', 'image-1'))
            return reference

        result = migrate(self.database, apply=True, backup_path=self.backup, manifest_path=self.manifest,
                         store=store_and_edit, resolve=self.resolve)
        self.assertEqual(result['migrated'], 0)
        self.assertEqual(result['changed_skipped'], 1)
        self.assertEqual(self.read_image(), b'new image bytes')
        self.assertEqual(self.read_image(self.backup), self.data)

    def test_existing_references_are_skipped_on_rerun(self):
        self.apply()
        result = migrate(self.database, apply=True, backup_path=self.root / 'backup2.sqlite',
                         manifest_path=self.root / 'migration2.jsonl', store=self.store, resolve=self.resolve)
        self.assertEqual(result['already_external'], 1)
        self.assertEqual(result['migrated'], 0)
        self.assertEqual(len(self.objects), 1)

    def test_apply_requires_r2_and_new_backup_manifest_paths(self):
        with patch.dict(os.environ, {'MEDIA_STORAGE_BACKEND': 'local'}), self.assertRaises(ValueError):
            self.apply()
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.manifest.exists())
        self.apply()
        with self.assertRaises(FileExistsError):
            self.apply()


if __name__ == '__main__':
    unittest.main()
