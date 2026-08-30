from pathlib import Path
import shutil
import sqlite3
from datetime import datetime


DB_PATH = Path("/workspaces/Golf-Coach/app/data/golf_coach.db")

if not DB_PATH.exists():
    raise FileNotFoundError(f"Database not found: {DB_PATH}")


# ---------------------------------------------------------
# BACKUP FIRST
# ---------------------------------------------------------

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = DB_PATH.with_name(f"golf_coach_pre_phase_5_1_1_{timestamp}.db")

shutil.copy2(DB_PATH, backup_path)

print(f"Backup created:")
print(f"  {backup_path}")


# ---------------------------------------------------------
# CONNECT
# ---------------------------------------------------------

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


def existing_columns(table_name: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


columns = existing_columns("session_videos")

print("\nExisting session_videos columns:")
for column in sorted(columns):
    print(f"  {column}")


# ---------------------------------------------------------
# PHASE 5.1.1 COLUMNS
# ---------------------------------------------------------

migrations = [
    (
        "video_type",
        """
        ALTER TABLE session_videos
        ADD COLUMN video_type VARCHAR(50)
        NOT NULL DEFAULT 'original_swing'
        """,
    ),
    (
        "parent_video_id",
        """
        ALTER TABLE session_videos
        ADD COLUMN parent_video_id VARCHAR(64)
        """,
    ),
    (
        "onform_processed",
        """
        ALTER TABLE session_videos
        ADD COLUMN onform_processed BOOLEAN
        NOT NULL DEFAULT 0
        """,
    ),
    (
        "analysis_status",
        """
        ALTER TABLE session_videos
        ADD COLUMN analysis_status VARCHAR(50)
        NOT NULL DEFAULT 'not_analyzed'
        """,
    ),
    (
        "updated_at",
        """
        ALTER TABLE session_videos
        ADD COLUMN updated_at DATETIME
        """,
    ),
]


for column_name, sql in migrations:
    if column_name in columns:
        print(f"Already exists: {column_name}")
        continue

    cursor.execute(sql)
    print(f"Added: {column_name}")


# ---------------------------------------------------------
# BACKFILL EXISTING ALPHA VIDEOS
# ---------------------------------------------------------

cursor.execute(
    """
    UPDATE session_videos
    SET video_type = 'original_swing'
    WHERE video_type IS NULL OR video_type = ''
    """
)

cursor.execute(
    """
    UPDATE session_videos
    SET analysis_status = 'not_analyzed'
    WHERE analysis_status IS NULL OR analysis_status = ''
    """
)

cursor.execute(
    """
    UPDATE session_videos
    SET onform_processed = 0
    WHERE onform_processed IS NULL
    """
)

cursor.execute(
    """
    UPDATE session_videos
    SET updated_at = created_at
    WHERE updated_at IS NULL
    """
)


# ---------------------------------------------------------
# INDEX
# ---------------------------------------------------------

cursor.execute(
    """
    CREATE INDEX IF NOT EXISTS
    ix_session_videos_video_type
    ON session_videos(video_type)
    """
)

cursor.execute(
    """
    CREATE INDEX IF NOT EXISTS
    ix_session_videos_parent_video_id
    ON session_videos(parent_video_id)
    """
)


conn.commit()


# ---------------------------------------------------------
# VERIFY
# ---------------------------------------------------------

print("\nUpdated session_videos schema:")

cursor.execute("PRAGMA table_info(session_videos)")

for row in cursor.fetchall():
    print(f"  {row[1]:22} {row[2]}")


cursor.execute("SELECT COUNT(*) FROM session_videos")
video_count = cursor.fetchone()[0]

print(f"\nExisting videos preserved: {video_count}")

conn.close()

print("\nPhase 5.1.1 database migration complete.")