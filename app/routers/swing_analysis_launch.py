from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.swing_analysis_store import create_analysis


router = APIRouter(
    prefix="/swing-analysis",
    tags=["Swing Analysis Launch"],
)


@router.get(
    "/video/{original_video_id}/open",
    name="swing_analysis_open_for_video",
)
def open_swing_analysis_for_video(
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

    return RedirectResponse(
        url=f"/swing-analysis/{analysis.id}/workspace",
        status_code=303,
    )
