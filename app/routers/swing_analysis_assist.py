from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SwingCheckpoint
from app.swing_analysis_store import get_analysis

router = APIRouter(prefix="/swing-analysis", tags=["Swing Analysis Assist"])

POSITION_FRACTIONS = {
    "P1": 0.000,
    "P2": 0.180,
    "P3": 0.360,
    "P4": 0.560,
    "P5": 0.640,
    "P6": 0.715,
    "P7": 0.760,
    "P8": 0.825,
    "P9": 0.905,
    "P10": 1.000,
}


def _rows(db: Session, analysis_id: str):
    stmt = (
        select(SwingCheckpoint)
        .where(SwingCheckpoint.analysis_id == str(analysis_id))
        .order_by(SwingCheckpoint.position_order.asc())
    )
    return list(db.scalars(stmt).all())


@router.post("/{analysis_id}/assist/checkpoints")
def assist_checkpoints(
    analysis_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    analysis = get_analysis(db, analysis_id)
    if analysis is None:
        raise HTTPException(404, "Swing analysis not found")

    try:
        p1_time = float(payload.get("p1_time"))
        p10_time = float(payload.get("p10_time"))
        fps = float(payload.get("fps") or 120)
    except (TypeError, ValueError):
        raise HTTPException(422, "P1 time, P10 time and FPS must be numeric.")

    if p1_time < 0:
        raise HTTPException(422, "P1 time cannot be negative.")
    if p10_time <= p1_time:
        raise HTTPException(422, "P10 must occur after P1.")
    if fps <= 0 or fps > 1000:
        raise HTTPException(422, "Invalid FPS.")

    overwrite = bool(payload.get("overwrite", False))
    duration = p10_time - p1_time
    checkpoints = _rows(db, analysis_id)

    if len(checkpoints) != 10:
        raise HTTPException(409, "Analysis does not contain all P1-P10 checkpoints.")

    result = []

    for cp in checkpoints:
        fraction = POSITION_FRACTIONS.get(cp.position)
        if fraction is None:
            continue

        estimated_time = p1_time + duration * fraction
        should_write = overwrite or cp.time_seconds is None or cp.position in {"P1", "P10"}

        if should_write:
            cp.time_seconds = round(estimated_time, 4)
            cp.frame_number = int(round(estimated_time * fps))
            cp.measurement_source = "Auto Assist"

        if (
            cp.x_factor is None
            and cp.pelvis_rotation is not None
            and cp.torso_rotation is not None
        ):
            cp.x_factor = round(
                float(cp.torso_rotation) - float(cp.pelvis_rotation),
                2,
            )

        result.append({
            "position": cp.position,
            "position_order": cp.position_order,
            "time_seconds": cp.time_seconds,
            "frame_number": cp.frame_number,
            "measurement_source": cp.measurement_source,
            "x_factor": cp.x_factor,
        })

    db.commit()

    return {
        "analysis_id": analysis_id,
        "fps": fps,
        "p1_time": p1_time,
        "p10_time": p10_time,
        "duration": round(duration, 4),
        "overwrite": overwrite,
        "checkpoints": result,
        "note": "Auto Assist estimates P2-P9 from coach-marked P1/P10. Verify each checkpoint visually.",
    }


@router.post("/{analysis_id}/assist/derive-x-factor")
def derive_x_factor(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    analysis = get_analysis(db, analysis_id)
    if analysis is None:
        raise HTTPException(404, "Swing analysis not found")

    changed = []
    for cp in _rows(db, analysis_id):
        if cp.pelvis_rotation is None or cp.torso_rotation is None:
            continue

        cp.x_factor = round(
            float(cp.torso_rotation) - float(cp.pelvis_rotation),
            2,
        )
        changed.append({
            "position": cp.position,
            "x_factor": cp.x_factor,
        })

    db.commit()
    return {"analysis_id": analysis_id, "updated": changed}
