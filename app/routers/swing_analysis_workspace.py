from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Shot, Student, SwingAnalysis
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


def _workspace_context(db: Session, analysis_id: str) -> dict[str, Any]:
    analysis = get_analysis(db, analysis_id)
    if analysis is None:
        raise HTTPException(404, "Swing analysis not found")

    shots = list(
        db.scalars(
            select(Shot)
            .where(Shot.session_id == analysis.session_id)
            .order_by(Shot.shot_number.asc(), Shot.created_at.asc())
        ).all()
    )

    latest_onform_import = _latest_onform_import(analysis)

    student = db.scalar(
        select(Student).where(Student.id == analysis.student_id)
    )
    primary_goal = (
        str(student.primary_goal or "").strip()
        if student is not None
        else ""
    )

    return {
        "analysis": analysis_to_dict(analysis),
        "shots": [_shot_dict(shot) for shot in shots],
        "latest_onform_import": latest_onform_import,
        "primary_goal": primary_goal,
    }


@router.get(
    "/{analysis_id}/workspace",
    response_class=RedirectResponse,
    name="swing_analysis_workspace",
)
def swing_analysis_workspace(
    request: Request,
    analysis_id: str,
    db: Session = Depends(get_db),
):
    _workspace_context(db, analysis_id)
    return RedirectResponse(
        url=f"/swing-analysis/{analysis_id}/onform-import",
        status_code=303,
    )


@router.get(
    "/{analysis_id}/onform-import",
    response_class=HTMLResponse,
    name="swing_analysis_onform_import",
)
def swing_analysis_onform_import(
    request: Request,
    analysis_id: str,
    db: Session = Depends(get_db),
):
    context = _workspace_context(db, analysis_id)
    return templates.TemplateResponse(
        request=request,
        name="swing_analysis_onform.html",
        context={
            "page_title": "Onform Import",
            **context,
        },
    )


@router.get(
    "/{analysis_id}/p-position",
    response_class=HTMLResponse,
    name="swing_analysis_p_position",
)
def swing_analysis_p_position(
    request: Request,
    analysis_id: str,
    db: Session = Depends(get_db),
):
    context = _workspace_context(db, analysis_id)
    return templates.TemplateResponse(
        request=request,
        name="swing_analysis_p_position.html",
        context={
            "page_title": "P-Position Analysis",
            **context,
        },
    )


@router.get(
    "/{analysis_id}/coaching",
    response_class=HTMLResponse,
    name="swing_analysis_coaching",
)
def swing_analysis_coaching(
    request: Request,
    analysis_id: str,
    db: Session = Depends(get_db),
):
    context = _workspace_context(db, analysis_id)
    return templates.TemplateResponse(
        request=request,
        name="swing_analysis_coaching.html",
        context={
            "page_title": "Coaching Analysis",
            **context,
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
        "extra_metrics_json": checkpoint.extra_metrics_json,
    }

# Phase 5.2.5A — Two-Screenshot Onform Import Fix
import json
from pathlib import Path
from uuid import uuid4
from fastapi import File, Form, UploadFile
from fastapi.responses import FileResponse
from app.models import SwingCheckpoint

ONFORM_SCREENSHOT_DIR = Path("app/media/onform_screenshots")
ONFORM_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

SHOT_SCREENSHOT_FIELDS = {
    "ball_speed", "club_speed", "smash_factor", "launch_angle",
    "launch_direction", "spin_rate", "spin_axis", "carry_distance",
    "total_distance", "apex_height", "attack_angle", "club_path",
    "club_face", "face_to_path", "offline_distance",
}
CHECKPOINT_SCREENSHOT_FIELDS = {
    "pelvis_rotation", "torso_rotation", "x_factor", "shoulder_tilt",
    "hip_tilt", "spine_tilt", "shaft_angle",
}
ANALYSIS_SCREENSHOT_FIELDS = {
    "max_pelvis_rotation", "max_torso_rotation", "max_x_factor",
    "max_x_factor_stretch", "address_spine_tilt", "top_shoulder_tilt",
    "top_hip_tilt",
}
ALLOWED_SCREENSHOT_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}
MAX_SCREENSHOT_BYTES = 15 * 1024 * 1024


def _latest_onform_import(analysis: SwingAnalysis) -> dict[str, Any] | None:
    try:
        extra = json.loads(analysis.extra_metrics_json or "{}")
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(extra, dict):
        return None
    imports = extra.get("onform_screenshot_imports")
    if not isinstance(imports, list) or not imports:
        return None
    latest = imports[-1]
    if not isinstance(latest, dict):
        return None

    result = dict(latest)
    screenshots = []
    for index, item in enumerate(latest.get("screenshots") or [], start=1):
        if not isinstance(item, dict):
            continue
        stored_name = str(item.get("stored_filename") or "")
        if not stored_name:
            continue
        saved = dict(item)
        saved["slot"] = index
        saved["url"] = (
            f"/swing-analysis/{analysis.id}/workspace/"
            f"onform-screenshot/{stored_name}"
        )
        saved["available"] = (ONFORM_SCREENSHOT_DIR / stored_name).is_file()
        screenshots.append(saved)
    result["screenshots"] = screenshots
    result["metrics"] = latest.get("metrics") if isinstance(latest.get("metrics"), dict) else {}
    result["kinematic_sequence"] = (
        latest.get("kinematic_sequence")
        if isinstance(latest.get("kinematic_sequence"), dict)
        else {}
    )
    return result


def _metric_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def _store_onform_screenshot(
    upload: UploadFile,
    *,
    session_id: str,
    analysis_id: str,
    slot: int,
) -> dict[str, str]:
    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED_SCREENSHOT_TYPES:
        raise HTTPException(415, "Use PNG, JPG/JPEG, or WEBP screenshots")

    data = await upload.read()
    if not data or len(data) > MAX_SCREENSHOT_BYTES:
        raise HTTPException(413, "Each screenshot must be between 1 byte and 15 MB")

    suffix = ALLOWED_SCREENSHOT_TYPES[content_type]
    stored_name = f"{session_id}_{analysis_id}_s{slot}_{uuid4().hex}{suffix}"
    path = ONFORM_SCREENSHOT_DIR / stored_name
    path.write_bytes(data)
    return {
        "stored_filename": stored_name,
        "original_filename": upload.filename or f"onform-screenshot-{slot}",
        "content_type": content_type,
    }


@router.post("/{analysis_id}/workspace/onform-screenshot", name="onform_screenshot_import")
async def onform_screenshot_import(
    analysis_id: str,
    screenshot_1: UploadFile | None = File(None),
    screenshot_2: UploadFile | None = File(None),
    screenshot_3: UploadFile | None = File(None),
    metrics_json: str = Form("{}"),
    sequence_json: str = Form("{}"),
    shot_id: str = Form(""),
    checkpoint_position: str = Form("P7"),
    verified: str = Form("false"),
    ocr_text_1: str = Form(""),
    ocr_text_2: str = Form(""),
    ocr_text_3: str = Form(""),
    conflicts_json: str = Form("[]"),
    db: Session = Depends(get_db),
):
    analysis = get_analysis(db, analysis_id)
    if analysis is None:
        raise HTTPException(404, "Swing analysis not found")

    is_verified = verified.lower() == "true"

    try:
        metrics = json.loads(metrics_json or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(422, "Invalid screenshot metrics") from exc
    if not isinstance(metrics, dict):
        raise HTTPException(422, "Screenshot metrics must be an object")

    try:
        sequence = json.loads(sequence_json or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(422, "Invalid kinematic sequence data") from exc
    if not isinstance(sequence, dict):
        raise HTTPException(422, "Kinematic sequence data must be an object")

    try:
        conflicts = json.loads(conflicts_json or "[]")
    except json.JSONDecodeError:
        conflicts = []
    if not isinstance(conflicts, list):
        conflicts = []

    previous = _latest_onform_import(analysis) or {}
    previous_screens = {
        int(item.get("slot")): item
        for item in (previous.get("screenshots") or [])
        if isinstance(item, dict) and item.get("slot")
    }

    stored: list[dict[str, str]] = []
    newly_stored: list[dict[str, str]] = []
    try:
        uploads = {1: screenshot_1, 2: screenshot_2, 3: screenshot_3}
        for slot in (1, 2, 3):
            upload = uploads[slot]
            if upload is not None and upload.filename:
                item = await _store_onform_screenshot(
                    upload,
                    session_id=analysis.session_id,
                    analysis_id=analysis.id,
                    slot=slot,
                )
                stored.append(item)
                newly_stored.append(item)
                continue

            previous_item = previous_screens.get(slot)
            if previous_item and previous_item.get("available"):
                stored.append({
                    "stored_filename": previous_item["stored_filename"],
                    "original_filename": previous_item.get(
                        "original_filename", f"onform-screenshot-{slot}"
                    ),
                    "content_type": previous_item.get("content_type", "image/png"),
                })
                continue

            if slot in (1, 2):
                raise HTTPException(
                    422,
                    "Choose Onform screenshots 1 and 2, or save them once before reusing evidence.",
                )

        # Evidence is saved immediately after extraction. Coach verification
        # is required only before committing metrics to Shot/Checkpoint data.
        if not is_verified:
            try:
                extra = json.loads(analysis.extra_metrics_json or "{}")
                if not isinstance(extra, dict):
                    extra = {}
            except (TypeError, json.JSONDecodeError):
                extra = {}

            imports = extra.setdefault("onform_screenshot_imports", [])
            imports.append({
                "phase": "5.2.7G",
                "status": "evidence_saved",
                "screenshots": stored,
                "shot_id": None,
                "checkpoint_position": checkpoint_position.upper().strip() or "P7",
                "verified": False,
                "metrics": metrics,
                "kinematic_sequence": sequence,
                "conflicts_at_extraction": conflicts,
                "ocr_text": {
                    "screenshot_1": ocr_text_1[:12000],
                    "screenshot_2": ocr_text_2[:12000],
                    "screenshot_3": ocr_text_3[:12000],
                },
            })
            analysis.extra_metrics_json = json.dumps(extra)
            db.commit()

            refreshed = get_analysis(db, analysis.id) or analysis
            return {
                "ok": True,
                "evidence_saved": True,
                "verified": False,
                "analysis": analysis_to_dict(refreshed),
                "saved_import": _latest_onform_import(refreshed),
            }

        selected_shot = None

        if shot_id == "__new__":
            existing_numbers = db.scalars(
                select(Shot.shot_number).where(
                    Shot.session_id == analysis.session_id
                )
            ).all()
            next_shot_number = (
                max(
                    [
                        int(number)
                        for number in existing_numbers
                        if number is not None
                    ],
                    default=0,
                )
                + 1
            )

            selected_shot = Shot(
                id=str(uuid4()),
                session_id=analysis.session_id,
                student_id=analysis.student_id,
                shot_number=next_shot_number,
                club="",
                shot_shape="",
                source="Onform Screenshot",
                included=True,
                raw_signature="",
            )
            db.add(selected_shot)
            analysis.shot_id = selected_shot.id

        elif shot_id:
            selected_shot = db.get(Shot, shot_id)
            if selected_shot is None or selected_shot.session_id != analysis.session_id:
                raise HTTPException(400, "Selected Shot Table record does not belong to this session")
            analysis.shot_id = selected_shot.id

        if selected_shot is not None:
            for field in SHOT_SCREENSHOT_FIELDS:
                value = _metric_float(metrics.get(field))
                if value is not None:
                    setattr(selected_shot, field, value)

            club = str(metrics.get("club") or "").strip()
            if club:
                selected_shot.club = club

            # If the screenshots provide both speeds but not Smash,
            # calculate it for the Shot Table without overwriting a
            # coach-verified screenshot value.
            if selected_shot.smash_factor is None:
                ball_speed = _metric_float(metrics.get("ball_speed"))
                club_speed = _metric_float(metrics.get("club_speed"))
                if (
                    ball_speed is not None
                    and club_speed is not None
                    and club_speed > 0
                ):
                    selected_shot.smash_factor = round(
                        ball_speed / club_speed,
                        3,
                    )

            selected_shot.source = "Onform Screenshot"

        checkpoint_position = checkpoint_position.upper().strip() or "P7"
        checkpoint = db.scalar(
            select(SwingCheckpoint).where(
                SwingCheckpoint.analysis_id == analysis.id,
                SwingCheckpoint.position == checkpoint_position,
            )
        )
        if checkpoint is not None:
            for field in CHECKPOINT_SCREENSHOT_FIELDS:
                value = _metric_float(metrics.get(field))
                if value is not None:
                    setattr(checkpoint, field, value)
            checkpoint.measurement_source = "Onform Screenshot"
            checkpoint.confidence = 1.0

        for field in ANALYSIS_SCREENSHOT_FIELDS:
            value = _metric_float(metrics.get(field))
            if value is not None:
                setattr(analysis, field, value)

        try:
            extra = json.loads(analysis.extra_metrics_json or "{}")
            if not isinstance(extra, dict):
                extra = {}
        except (TypeError, json.JSONDecodeError):
            extra = {}

        imports = extra.setdefault("onform_screenshot_imports", [])
        imports.append({
            "phase": "5.2.7G",
            "status": "verified_committed",
            "screenshots": stored,
            "shot_id": selected_shot.id if selected_shot else None,
            "checkpoint_position": checkpoint_position,
            "verified": True,
            "metrics": metrics,
            "kinematic_sequence": sequence,
            "conflicts_at_extraction": conflicts,
            "ocr_text": {
                "screenshot_1": ocr_text_1[:12000],
                "screenshot_2": ocr_text_2[:12000],
                "screenshot_3": ocr_text_3[:12000],
            },
        })
        analysis.extra_metrics_json = json.dumps(extra)
        db.commit()
    except Exception:
        db.rollback()
        for item in newly_stored:
            (ONFORM_SCREENSHOT_DIR / item["stored_filename"]).unlink(missing_ok=True)
        raise

    refreshed = get_analysis(db, analysis.id) or analysis
    return {
        "ok": True,
        "evidence_saved": True,
        "verified": True,
        "shot_committed": selected_shot is not None,
        "shot_id": selected_shot.id if selected_shot is not None else None,
        "analysis": analysis_to_dict(refreshed),
        "saved_import": _latest_onform_import(refreshed),
        "screenshot_urls": [
            f"/swing-analysis/{analysis.id}/workspace/onform-screenshot/{item['stored_filename']}"
            for item in stored
        ],
    }


@router.get("/{analysis_id}/workspace/onform-screenshot/{stored_name}", name="onform_screenshot_evidence")
def onform_screenshot_evidence(
    analysis_id: str,
    stored_name: str,
    db: Session = Depends(get_db),
):
    analysis = get_analysis(db, analysis_id)
    if analysis is None:
        raise HTTPException(404, "Swing analysis not found")
    if Path(stored_name).name != stored_name or not stored_name.startswith(f"{analysis.session_id}_{analysis.id}_"):
        raise HTTPException(404, "Screenshot not found")
    path = ONFORM_SCREENSHOT_DIR / stored_name
    if not path.is_file():
        raise HTTPException(404, "Screenshot not found")
    return FileResponse(path)
