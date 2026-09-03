from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Shot, SwingAnalysis
from app.swing_analysis_store import (
    analysis_to_dict,
    get_analysis,
    link_garmin_shot,
    update_checkpoint,
)


router = APIRouter(
    prefix="/swing-analysis",
    tags=["Swing Analysis Workspace"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


ANALYSIS_TEXT_FIELDS = {
    "tgm_pattern",
    "tgm_stationary_head",
    "tgm_balance",
    "tgm_rhythm",
    "tgm_club_path",
    "tgm_clubface_alignment",
    "tgm_timing",
    "tgm_power_accumulator_1",
    "tgm_power_accumulator_2",
    "tgm_power_accumulator_3",
    "tgm_power_accumulator_4",
    "tgm_plane_notes",
    "tgm_component_notes",

    "tpi_swing_characteristics",
    "tpi_mobility_observations",
    "tpi_stability_observations",
    "tpi_balance_observations",
    "tpi_sequencing_observations",
    "tpi_screen_reason",

    "garmin_summary",
    "ball_flight_summary",
    "movement_to_impact_summary",

    "primary_finding",
    "secondary_findings",
    "likely_compensations",
    "primary_priority",
    "coaching_observations",
    "recommended_drills",
    "player_feels",
    "coach_notes",
}

ANALYSIS_FLOAT_FIELDS = {
    "max_pelvis_rotation",
    "max_torso_rotation",
    "max_x_factor",
    "max_x_factor_stretch",
    "address_spine_tilt",
    "top_shoulder_tilt",
    "top_hip_tilt",
    "finish_balance_offset",
    "head_c7_stability_score",
    "rhythm_score",
    "sequencing_score",
}

ANALYSIS_BOOL_FIELDS = {
    "tpi_physical_screen_recommended",
}


def _shot_dict(shot: Shot) -> dict[str, Any]:
    return {
        "id": shot.id,
        "shot_number": shot.shot_number,
        "club": shot.club,
        "shot_shape": shot.shot_shape,
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


@router.get(
    "/{analysis_id}/workspace",
    response_class=HTMLResponse,
    name="swing_analysis_workspace",
)
def swing_analysis_workspace(
    request: Request,
    analysis_id: str,
    db: Session = Depends(get_db),
):
    analysis = get_analysis(
        db,
        analysis_id,
    )

    if analysis is None:
        raise HTTPException(
            404,
            "Swing analysis not found",
        )

    shots = list(
        db.scalars(
            select(Shot)
            .where(
                Shot.session_id == analysis.session_id
            )
            .order_by(
                Shot.shot_number.asc(),
                Shot.created_at.asc(),
            )
        ).all()
    )

    return templates.TemplateResponse(
        request=request,
        name="swing_analysis_workspace.html",
        context={
            "page_title": "Swing Analysis",
            "analysis": analysis_to_dict(analysis),
            "shots": [
                _shot_dict(shot)
                for shot in shots
            ],
        },
    )


@router.patch(
    "/{analysis_id}/workspace",
    name="swing_analysis_workspace_update",
)
def swing_analysis_workspace_update(
    analysis_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
):
    analysis = get_analysis(
        db,
        analysis_id,
    )

    if analysis is None:
        raise HTTPException(
            404,
            "Swing analysis not found",
        )

    for key in ANALYSIS_TEXT_FIELDS:
        if key in payload:
            value = payload[key]
            setattr(
                analysis,
                key,
                "" if value is None else str(value),
            )

    for key in ANALYSIS_FLOAT_FIELDS:
        if key not in payload:
            continue

        value = payload[key]

        if value in ("", None):
            setattr(
                analysis,
                key,
                None,
            )
            continue

        try:
            setattr(
                analysis,
                key,
                float(value),
            )
        except (TypeError, ValueError):
            raise HTTPException(
                422,
                f"{key} must be numeric",
            )

    for key in ANALYSIS_BOOL_FIELDS:
        if key in payload:
            setattr(
                analysis,
                key,
                bool(payload[key]),
            )

    if "status" in payload:
        status = str(
            payload["status"] or ""
        ).strip()

        allowed_statuses = {
            "draft",
            "measured",
            "analyzed",
            "coach_reviewed",
            "complete",
        }

        if status not in allowed_statuses:
            raise HTTPException(
                422,
                "Invalid analysis status",
            )

        analysis.status = status

    db.commit()

    refreshed = get_analysis(
        db,
        analysis.id,
    )

    return analysis_to_dict(
        refreshed or analysis
    )


@router.post(
    "/{analysis_id}/workspace/shot/{shot_id}",
    name="swing_analysis_workspace_link_shot",
)
def swing_analysis_workspace_link_shot(
    analysis_id: str,
    shot_id: str,
    db: Session = Depends(get_db),
):
    try:
        analysis = link_garmin_shot(
            db,
            analysis_id,
            shot_id,
        )
    except ValueError as exc:
        raise HTTPException(
            400,
            str(exc),
        )

    return analysis_to_dict(
        analysis
    )


@router.patch(
    "/{analysis_id}/workspace/checkpoint/{position}",
    name="swing_analysis_workspace_checkpoint_update",
)
def swing_analysis_workspace_checkpoint_update(
    analysis_id: str,
    position: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
):
    try:
        checkpoint = update_checkpoint(
            db,
            analysis_id,
            position,
            payload,
        )
    except ValueError as exc:
        raise HTTPException(
            400,
            str(exc),
        )

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
        "tgm_observation": checkpoint.tgm_observation,
        "tpi_observation": checkpoint.tpi_observation,
        "biomechanical_observation": checkpoint.biomechanical_observation,
        "coaching_observation": checkpoint.coaching_observation,
        "measurement_source": checkpoint.measurement_source,
        "confidence": checkpoint.confidence,
    }
