from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import SessionVideo, Shot, SwingAnalysis, SwingCheckpoint


P_POSITIONS: tuple[tuple[str, int], ...] = (
    ("P1", 1),
    ("P2", 2),
    ("P3", 3),
    ("P4", 4),
    ("P5", 5),
    ("P6", 6),
    ("P7", 7),
    ("P8", 8),
    ("P9", 9),
    ("P10", 10),
)


def _video_to_dict(video: SessionVideo | None) -> dict[str, Any] | None:
    if video is None:
        return None

    return {
        "id": video.id,
        "session_id": video.session_id,
        "student_id": video.student_id,
        "title": video.title,
        "video_type": video.video_type,
        "source": video.source,
        "camera_view": video.camera_view,
        "club": video.club,
        "shot_number": video.shot_number,
        "onform_url": video.onform_url,
        "original_filename": video.original_filename,
        "stored_filename": video.stored_filename,
    }


def _shot_to_dict(shot: Shot | None) -> dict[str, Any] | None:
    if shot is None:
        return None

    return {
        "id": shot.id,
        "session_id": shot.session_id,
        "student_id": shot.student_id,
        "shot_number": shot.shot_number,
        "club": shot.club,
        "shot_shape": shot.shot_shape,
        "source": shot.source,
        "included": bool(shot.included),
        "ball_speed": shot.ball_speed,
        "club_speed": shot.club_speed,
        "smash_factor": shot.smash_factor,
        "launch_angle": shot.launch_angle,
        "launch_direction": shot.launch_direction,
        "spin_rate": shot.spin_rate,
        "spin_axis": shot.spin_axis,
        "carry_distance": shot.carry_distance,
        "total_distance": shot.total_distance,
        "apex_height": shot.apex_height,
        "attack_angle": shot.attack_angle,
        "club_path": shot.club_path,
        "club_face": shot.club_face,
        "face_to_path": shot.face_to_path,
        "offline_distance": shot.offline_distance,
    }


def checkpoint_to_dict(checkpoint: SwingCheckpoint) -> dict[str, Any]:
    return {
        "id": checkpoint.id,
        "analysis_id": checkpoint.analysis_id,
        "position": checkpoint.position,
        "position_order": checkpoint.position_order,
        "frame_number": checkpoint.frame_number,
        "time_seconds": checkpoint.time_seconds,
        "pelvis_rotation": checkpoint.pelvis_rotation,
        "torso_rotation": checkpoint.torso_rotation,
        "x_factor": checkpoint.x_factor,
        "shoulder_tilt": checkpoint.shoulder_tilt,
        "hip_tilt": checkpoint.hip_tilt,
        "spine_tilt": checkpoint.spine_tilt,
        "shaft_angle": checkpoint.shaft_angle,
        "lead_arm_angle": checkpoint.lead_arm_angle,
        "trail_arm_angle": checkpoint.trail_arm_angle,
        "head_x": checkpoint.head_x,
        "head_y": checkpoint.head_y,
        "pelvis_x": checkpoint.pelvis_x,
        "pelvis_y": checkpoint.pelvis_y,
        "hand_path_x": checkpoint.hand_path_x,
        "hand_path_y": checkpoint.hand_path_y,
        "tgm_observation": checkpoint.tgm_observation,
        "tpi_observation": checkpoint.tpi_observation,
        "biomechanical_observation": checkpoint.biomechanical_observation,
        "coaching_observation": checkpoint.coaching_observation,
        "measurement_source": checkpoint.measurement_source,
        "confidence": checkpoint.confidence,
        "extra_metrics_json": checkpoint.extra_metrics_json,
    }


def analysis_to_dict(analysis: SwingAnalysis) -> dict[str, Any]:
    return {
        "id": analysis.id,
        "session_id": analysis.session_id,
        "student_id": analysis.student_id,
        "original_video_id": analysis.original_video_id,
        "onform_analysis_video_id": analysis.onform_analysis_video_id,
        "shot_id": analysis.shot_id,
        "status": analysis.status,
        "camera_view": analysis.camera_view,
        "club": analysis.club,

        "tgm_pattern": analysis.tgm_pattern,
        "tgm_stationary_head": analysis.tgm_stationary_head,
        "tgm_balance": analysis.tgm_balance,
        "tgm_rhythm": analysis.tgm_rhythm,
        "tgm_club_path": analysis.tgm_club_path,
        "tgm_clubface_alignment": analysis.tgm_clubface_alignment,
        "tgm_timing": analysis.tgm_timing,
        "tgm_power_accumulator_1": analysis.tgm_power_accumulator_1,
        "tgm_power_accumulator_2": analysis.tgm_power_accumulator_2,
        "tgm_power_accumulator_3": analysis.tgm_power_accumulator_3,
        "tgm_power_accumulator_4": analysis.tgm_power_accumulator_4,
        "tgm_plane_notes": analysis.tgm_plane_notes,
        "tgm_component_notes": analysis.tgm_component_notes,

        "tpi_swing_characteristics": analysis.tpi_swing_characteristics,
        "tpi_mobility_observations": analysis.tpi_mobility_observations,
        "tpi_stability_observations": analysis.tpi_stability_observations,
        "tpi_balance_observations": analysis.tpi_balance_observations,
        "tpi_sequencing_observations": analysis.tpi_sequencing_observations,
        "tpi_physical_screen_recommended": bool(
            analysis.tpi_physical_screen_recommended
        ),
        "tpi_screen_reason": analysis.tpi_screen_reason,

        "max_pelvis_rotation": analysis.max_pelvis_rotation,
        "max_torso_rotation": analysis.max_torso_rotation,
        "max_x_factor": analysis.max_x_factor,
        "max_x_factor_stretch": analysis.max_x_factor_stretch,
        "address_spine_tilt": analysis.address_spine_tilt,
        "top_shoulder_tilt": analysis.top_shoulder_tilt,
        "top_hip_tilt": analysis.top_hip_tilt,
        "finish_balance_offset": analysis.finish_balance_offset,
        "head_c7_stability_score": analysis.head_c7_stability_score,
        "rhythm_score": analysis.rhythm_score,
        "sequencing_score": analysis.sequencing_score,

        "garmin_summary": analysis.garmin_summary,
        "ball_flight_summary": analysis.ball_flight_summary,
        "movement_to_impact_summary": analysis.movement_to_impact_summary,

        "primary_finding": analysis.primary_finding,
        "secondary_findings": analysis.secondary_findings,
        "likely_compensations": analysis.likely_compensations,
        "primary_priority": analysis.primary_priority,
        "coaching_observations": analysis.coaching_observations,
        "recommended_drills": analysis.recommended_drills,
        "player_feels": analysis.player_feels,
        "coach_notes": analysis.coach_notes,
        "extra_metrics_json": analysis.extra_metrics_json,

        "original_video": _video_to_dict(analysis.original_video),
        "onform_analysis_video": _video_to_dict(analysis.onform_analysis_video),
        "shot": _shot_to_dict(analysis.shot),
        "checkpoints": [
            checkpoint_to_dict(checkpoint)
            for checkpoint in sorted(
                analysis.checkpoints,
                key=lambda item: item.position_order,
            )
        ],
    }


def get_analysis(db: Session, analysis_id: str) -> SwingAnalysis | None:
    stmt = (
        select(SwingAnalysis)
        .where(SwingAnalysis.id == str(analysis_id))
        .options(
            selectinload(SwingAnalysis.checkpoints),
            selectinload(SwingAnalysis.original_video),
            selectinload(SwingAnalysis.onform_analysis_video),
            selectinload(SwingAnalysis.shot),
        )
    )
    return db.scalar(stmt)


def get_analysis_for_original_video(
    db: Session,
    original_video_id: str,
) -> SwingAnalysis | None:
    stmt = (
        select(SwingAnalysis)
        .where(SwingAnalysis.original_video_id == str(original_video_id))
        .order_by(SwingAnalysis.created_at.desc())
        .options(
            selectinload(SwingAnalysis.checkpoints),
            selectinload(SwingAnalysis.original_video),
            selectinload(SwingAnalysis.onform_analysis_video),
            selectinload(SwingAnalysis.shot),
        )
    )
    return db.scalars(stmt).first()


def list_session_analyses(
    db: Session,
    session_id: str,
) -> list[SwingAnalysis]:
    stmt = (
        select(SwingAnalysis)
        .where(SwingAnalysis.session_id == str(session_id))
        .order_by(SwingAnalysis.created_at.desc())
        .options(
            selectinload(SwingAnalysis.checkpoints),
            selectinload(SwingAnalysis.original_video),
            selectinload(SwingAnalysis.onform_analysis_video),
            selectinload(SwingAnalysis.shot),
        )
    )
    return list(db.scalars(stmt).all())


def _find_linked_onform_analysis(
    db: Session,
    original_video: SessionVideo,
) -> SessionVideo | None:
    stmt = (
        select(SessionVideo)
        .where(
            SessionVideo.parent_video_id == original_video.id,
            SessionVideo.video_type == "onform_analysis",
        )
        .order_by(SessionVideo.created_at.desc())
    )
    return db.scalars(stmt).first()


def _find_matching_garmin_shot(
    db: Session,
    original_video: SessionVideo,
) -> Shot | None:
    if original_video.shot_number is not None:
        stmt = (
            select(Shot)
            .where(
                Shot.session_id == original_video.session_id,
                Shot.shot_number == original_video.shot_number,
            )
            .order_by(Shot.created_at.asc())
        )
        shot = db.scalars(stmt).first()
        if shot is not None:
            return shot

    if original_video.club:
        stmt = (
            select(Shot)
            .where(
                Shot.session_id == original_video.session_id,
                Shot.club == original_video.club,
                Shot.included.is_(True),
            )
            .order_by(Shot.created_at.asc())
        )
        shot = db.scalars(stmt).first()
        if shot is not None:
            return shot

    return None


def initialize_p_checkpoints(
    db: Session,
    analysis: SwingAnalysis,
) -> list[SwingCheckpoint]:
    existing_positions = {
        checkpoint.position
        for checkpoint in analysis.checkpoints
    }

    created: list[SwingCheckpoint] = []

    for position, order in P_POSITIONS:
        if position in existing_positions:
            continue

        checkpoint = SwingCheckpoint(
            id=str(uuid4()),
            analysis_id=analysis.id,
            position=position,
            position_order=order,
            measurement_source="Manual",
        )
        db.add(checkpoint)
        created.append(checkpoint)

    if created:
        db.flush()

    return created


def create_analysis(
    db: Session,
    original_video_id: str,
) -> SwingAnalysis:
    original = db.get(
        SessionVideo,
        str(original_video_id),
    )

    if original is None:
        raise ValueError("Original swing video was not found.")

    if original.video_type != "original_swing":
        raise ValueError(
            "SwingAnalysis must be created from an Original Swing video."
        )

    existing = get_analysis_for_original_video(
        db,
        original.id,
    )

    if existing is not None:
        initialize_p_checkpoints(
            db,
            existing,
        )
        db.commit()
        return get_analysis(db, existing.id) or existing

    linked_onform = _find_linked_onform_analysis(
        db,
        original,
    )

    matching_shot = _find_matching_garmin_shot(
        db,
        original,
    )

    analysis = SwingAnalysis(
        id=str(uuid4()),
        session_id=original.session_id,
        student_id=original.student_id,
        original_video_id=original.id,
        onform_analysis_video_id=(
            linked_onform.id
            if linked_onform is not None
            else None
        ),
        shot_id=(
            matching_shot.id
            if matching_shot is not None
            else None
        ),
        status="draft",
        camera_view=original.camera_view or "",
        club=original.club or "",
    )

    db.add(analysis)
    db.flush()

    initialize_p_checkpoints(
        db,
        analysis,
    )

    db.commit()

    return get_analysis(db, analysis.id) or analysis


def link_onform_analysis(
    db: Session,
    analysis_id: str,
    onform_video_id: str,
) -> SwingAnalysis:
    analysis = get_analysis(
        db,
        analysis_id,
    )

    if analysis is None:
        raise ValueError("Swing analysis was not found.")

    video = db.get(
        SessionVideo,
        str(onform_video_id),
    )

    if video is None:
        raise ValueError("Onform analysis video was not found.")

    if video.video_type != "onform_analysis":
        raise ValueError("Selected video is not an Onform Analysis.")

    if video.session_id != analysis.session_id:
        raise ValueError(
            "Onform analysis must belong to the same coaching session."
        )

    if video.student_id != analysis.student_id:
        raise ValueError(
            "Onform analysis must belong to the same student."
        )

    if video.parent_video_id != analysis.original_video_id:
        raise ValueError(
            "Onform analysis is not linked to this Original Swing."
        )

    analysis.onform_analysis_video_id = video.id

    db.commit()

    return get_analysis(db, analysis.id) or analysis


def link_garmin_shot(
    db: Session,
    analysis_id: str,
    shot_id: str,
) -> SwingAnalysis:
    analysis = get_analysis(
        db,
        analysis_id,
    )

    if analysis is None:
        raise ValueError("Swing analysis was not found.")

    shot = db.get(
        Shot,
        str(shot_id),
    )

    if shot is None:
        raise ValueError("Garmin shot was not found.")

    if shot.session_id != analysis.session_id:
        raise ValueError(
            "Garmin shot must belong to the same coaching session."
        )

    if shot.student_id != analysis.student_id:
        raise ValueError(
            "Garmin shot must belong to the same student."
        )

    analysis.shot_id = shot.id

    if not analysis.club and shot.club:
        analysis.club = shot.club

    db.commit()

    return get_analysis(db, analysis.id) or analysis


def update_checkpoint(
    db: Session,
    analysis_id: str,
    position: str,
    values: dict[str, Any],
) -> SwingCheckpoint:
    normalized = str(position).upper().strip()

    valid_positions = {
        item[0]
        for item in P_POSITIONS
    }

    if normalized not in valid_positions:
        raise ValueError("Position must be P1 through P10.")

    stmt = select(SwingCheckpoint).where(
        SwingCheckpoint.analysis_id == str(analysis_id),
        SwingCheckpoint.position == normalized,
    )

    checkpoint = db.scalar(stmt)

    if checkpoint is None:
        analysis = get_analysis(
            db,
            analysis_id,
        )

        if analysis is None:
            raise ValueError("Swing analysis was not found.")

        order = dict(P_POSITIONS)[normalized]

        checkpoint = SwingCheckpoint(
            id=str(uuid4()),
            analysis_id=analysis.id,
            position=normalized,
            position_order=order,
        )
        db.add(checkpoint)

    allowed_fields = {
        "frame_number",
        "time_seconds",
        "pelvis_rotation",
        "torso_rotation",
        "x_factor",
        "shoulder_tilt",
        "hip_tilt",
        "spine_tilt",
        "shaft_angle",
        "lead_arm_angle",
        "trail_arm_angle",
        "head_x",
        "head_y",
        "pelvis_x",
        "pelvis_y",
        "hand_path_x",
        "hand_path_y",
        "tgm_observation",
        "tpi_observation",
        "biomechanical_observation",
        "coaching_observation",
        "measurement_source",
        "confidence",
        "extra_metrics_json",
    }

    for key, value in values.items():
        if key in allowed_fields:
            setattr(
                checkpoint,
                key,
                value,
            )

    db.commit()
    db.refresh(checkpoint)

    return checkpoint
