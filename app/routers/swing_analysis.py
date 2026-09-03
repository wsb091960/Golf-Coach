from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SessionVideo
from app.swing_analysis_store import (
    analysis_to_dict,
    checkpoint_to_dict,
    create_analysis,
    get_analysis,
    link_garmin_shot,
    link_onform_analysis,
    list_session_analyses,
    update_checkpoint,
)


router = APIRouter(
    prefix="/swing-analysis",
    tags=["Swing Analysis"],
)


@router.post(
    "/video/{original_video_id}/create",
    name="swing_analysis_create",
)
def create_swing_analysis(
    original_video_id: str,
    db: Session = Depends(get_db),
):
    try:
        analysis = create_analysis(
            db,
            original_video_id,
        )
    except ValueError as exc:
        raise HTTPException(
            400,
            str(exc),
        )

    return analysis_to_dict(
        analysis
    )


@router.get(
    "/{analysis_id}",
    name="swing_analysis_detail",
)
def swing_analysis_detail(
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

    return analysis_to_dict(
        analysis
    )


@router.get(
    "/session/{session_id}",
    name="swing_analysis_session_list",
)
def swing_analysis_session_list(
    session_id: str,
    db: Session = Depends(get_db),
):
    analyses = list_session_analyses(
        db,
        session_id,
    )

    return {
        "session_id": session_id,
        "count": len(analyses),
        "analyses": [
            analysis_to_dict(
                analysis
            )
            for analysis in analyses
        ],
    }


@router.post(
    "/{analysis_id}/onform/{onform_video_id}",
    name="swing_analysis_link_onform",
)
def swing_analysis_link_onform(
    analysis_id: str,
    onform_video_id: str,
    db: Session = Depends(get_db),
):
    try:
        analysis = link_onform_analysis(
            db,
            analysis_id,
            onform_video_id,
        )
    except ValueError as exc:
        raise HTTPException(
            400,
            str(exc),
        )

    return analysis_to_dict(
        analysis
    )


@router.post(
    "/{analysis_id}/shot/{shot_id}",
    name="swing_analysis_link_shot",
)
def swing_analysis_link_shot(
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
    "/{analysis_id}/checkpoint/{position}",
    name="swing_analysis_checkpoint_update",
)
def swing_analysis_checkpoint_update(
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

    return checkpoint_to_dict(
        checkpoint
    )


@router.get(
    "/video/{original_video_id}/existing",
    name="swing_analysis_existing_for_video",
)
def swing_analysis_existing_for_video(
    original_video_id: str,
    db: Session = Depends(get_db),
):
    original = db.get(
        SessionVideo,
        str(original_video_id),
    )

    if original is None:
        raise HTTPException(
            404,
            "Original swing video not found",
        )

    analysis = create_analysis(
        db,
        original_video_id,
    )

    return analysis_to_dict(
        analysis
    )
