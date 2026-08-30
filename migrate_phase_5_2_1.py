"""
WSBCO Golf Coach
Phase 5.2.1 — SwingAnalysis data-model migration

Creates:
    swing_analyses
    swing_checkpoints

This migration is additive only. It does not modify or delete
existing students, sessions, shots, or videos.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import sqlite3


DB_PATH = Path("/workspaces/Golf-Coach/app/data/golf_coach.db")

if not DB_PATH.exists():
    raise FileNotFoundError(f"Database not found: {DB_PATH}")


timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = DB_PATH.with_name(
    f"golf_coach_pre_phase_5_2_1_{timestamp}.db"
)

shutil.copy2(DB_PATH, backup_path)

print("Backup created:")
print(f"  {backup_path}")


conn = sqlite3.connect(DB_PATH)

try:
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS swing_analyses (
            id VARCHAR(64) PRIMARY KEY NOT NULL,

            session_id VARCHAR(64) NOT NULL,
            student_id VARCHAR(64) NOT NULL,
            original_video_id VARCHAR(64) NOT NULL,
            onform_analysis_video_id VARCHAR(64),
            shot_id VARCHAR(64),

            status VARCHAR(50) NOT NULL DEFAULT 'draft',
            camera_view VARCHAR(50) NOT NULL DEFAULT '',
            club VARCHAR(100) NOT NULL DEFAULT '',

            tgm_pattern VARCHAR(50) NOT NULL DEFAULT 'undetermined',
            tgm_stationary_head TEXT NOT NULL DEFAULT '',
            tgm_balance TEXT NOT NULL DEFAULT '',
            tgm_rhythm TEXT NOT NULL DEFAULT '',
            tgm_club_path TEXT NOT NULL DEFAULT '',
            tgm_clubface_alignment TEXT NOT NULL DEFAULT '',
            tgm_timing TEXT NOT NULL DEFAULT '',
            tgm_power_accumulator_1 TEXT NOT NULL DEFAULT '',
            tgm_power_accumulator_2 TEXT NOT NULL DEFAULT '',
            tgm_power_accumulator_3 TEXT NOT NULL DEFAULT '',
            tgm_power_accumulator_4 TEXT NOT NULL DEFAULT '',
            tgm_plane_notes TEXT NOT NULL DEFAULT '',
            tgm_component_notes TEXT NOT NULL DEFAULT '',

            tpi_swing_characteristics TEXT NOT NULL DEFAULT '',
            tpi_mobility_observations TEXT NOT NULL DEFAULT '',
            tpi_stability_observations TEXT NOT NULL DEFAULT '',
            tpi_balance_observations TEXT NOT NULL DEFAULT '',
            tpi_sequencing_observations TEXT NOT NULL DEFAULT '',
            tpi_physical_screen_recommended BOOLEAN NOT NULL DEFAULT 0,
            tpi_screen_reason TEXT NOT NULL DEFAULT '',

            max_pelvis_rotation FLOAT,
            max_torso_rotation FLOAT,
            max_x_factor FLOAT,
            max_x_factor_stretch FLOAT,
            address_spine_tilt FLOAT,
            top_shoulder_tilt FLOAT,
            top_hip_tilt FLOAT,
            finish_balance_offset FLOAT,
            head_c7_stability_score FLOAT,
            rhythm_score FLOAT,
            sequencing_score FLOAT,

            garmin_summary TEXT NOT NULL DEFAULT '',
            ball_flight_summary TEXT NOT NULL DEFAULT '',
            movement_to_impact_summary TEXT NOT NULL DEFAULT '',

            primary_finding TEXT NOT NULL DEFAULT '',
            secondary_findings TEXT NOT NULL DEFAULT '',
            likely_compensations TEXT NOT NULL DEFAULT '',
            primary_priority TEXT NOT NULL DEFAULT '',
            coaching_observations TEXT NOT NULL DEFAULT '',
            recommended_drills TEXT NOT NULL DEFAULT '',
            player_feels TEXT NOT NULL DEFAULT '',
            coach_notes TEXT NOT NULL DEFAULT '',
            extra_metrics_json TEXT NOT NULL DEFAULT '{}',

            created_at DATETIME,
            updated_at DATETIME,

            FOREIGN KEY(session_id)
                REFERENCES sessions(id)
                ON DELETE CASCADE,

            FOREIGN KEY(student_id)
                REFERENCES students(id)
                ON DELETE CASCADE,

            FOREIGN KEY(original_video_id)
                REFERENCES session_videos(id)
                ON DELETE CASCADE,

            FOREIGN KEY(onform_analysis_video_id)
                REFERENCES session_videos(id)
                ON DELETE SET NULL,

            FOREIGN KEY(shot_id)
                REFERENCES shots(id)
                ON DELETE SET NULL
        );


        CREATE TABLE IF NOT EXISTS swing_checkpoints (
            id VARCHAR(64) PRIMARY KEY NOT NULL,

            analysis_id VARCHAR(64) NOT NULL,

            position VARCHAR(10) NOT NULL,
            position_order INTEGER NOT NULL DEFAULT 1,

            frame_number INTEGER,
            time_seconds FLOAT,

            pelvis_rotation FLOAT,
            torso_rotation FLOAT,
            x_factor FLOAT,
            shoulder_tilt FLOAT,
            hip_tilt FLOAT,
            spine_tilt FLOAT,
            shaft_angle FLOAT,
            lead_arm_angle FLOAT,
            trail_arm_angle FLOAT,

            head_x FLOAT,
            head_y FLOAT,
            pelvis_x FLOAT,
            pelvis_y FLOAT,
            hand_path_x FLOAT,
            hand_path_y FLOAT,

            tgm_observation TEXT NOT NULL DEFAULT '',
            tpi_observation TEXT NOT NULL DEFAULT '',
            biomechanical_observation TEXT NOT NULL DEFAULT '',
            coaching_observation TEXT NOT NULL DEFAULT '',

            measurement_source VARCHAR(50) NOT NULL DEFAULT 'Manual',
            confidence FLOAT,

            extra_metrics_json TEXT NOT NULL DEFAULT '{}',

            created_at DATETIME,
            updated_at DATETIME,

            FOREIGN KEY(analysis_id)
                REFERENCES swing_analyses(id)
                ON DELETE CASCADE,

            CONSTRAINT uq_swing_checkpoint_analysis_position
                UNIQUE(analysis_id, position)
        );


        CREATE INDEX IF NOT EXISTS
            ix_swing_analyses_session_id
            ON swing_analyses(session_id);

        CREATE INDEX IF NOT EXISTS
            ix_swing_analyses_student_id
            ON swing_analyses(student_id);

        CREATE INDEX IF NOT EXISTS
            ix_swing_analyses_original_video_id
            ON swing_analyses(original_video_id);

        CREATE INDEX IF NOT EXISTS
            ix_swing_analyses_onform_analysis_video_id
            ON swing_analyses(onform_analysis_video_id);

        CREATE INDEX IF NOT EXISTS
            ix_swing_analyses_shot_id
            ON swing_analyses(shot_id);

        CREATE INDEX IF NOT EXISTS
            ix_swing_analyses_status
            ON swing_analyses(status);

        CREATE INDEX IF NOT EXISTS
            ix_swing_checkpoints_analysis_id
            ON swing_checkpoints(analysis_id);

        CREATE INDEX IF NOT EXISTS
            ix_swing_checkpoints_position
            ON swing_checkpoints(position);
        """
    )

    conn.commit()

    analysis_count = conn.execute(
        "SELECT COUNT(*) FROM swing_analyses"
    ).fetchone()[0]

    checkpoint_count = conn.execute(
        "SELECT COUNT(*) FROM swing_checkpoints"
    ).fetchone()[0]

    print()
    print("Phase 5.2.1 migration complete.")
    print(f"Swing analyses:   {analysis_count}")
    print(f"Swing checkpoints:{checkpoint_count}")

finally:
    conn.close()
