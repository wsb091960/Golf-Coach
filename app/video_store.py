from __future__ import annotations
from pathlib import Path
from typing import Any
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import SessionVideo

APP_DIR = Path(__file__).resolve().parent
VIDEO_ROOT = APP_DIR / "media" / "session_videos"
VIDEO_ROOT.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
MAX_VIDEO_BYTES = 750 * 1024 * 1024

def video_to_dict(video: SessionVideo) -> dict[str, Any]:
    return {
        "id": video.id, "session_id": video.session_id, "student_id": video.student_id,
        "title": video.title, "camera_view": video.camera_view, "club": video.club,
        "shot_number": video.shot_number, "notes": video.notes,
        "original_filename": video.original_filename, "stored_filename": video.stored_filename,
        "content_type": video.content_type, "source": video.source,
        "onform_url": video.onform_url,
        "created_at": video.created_at.isoformat() if video.created_at else "",
    }

def list_session_videos(db: Session, session_id: str) -> list[dict[str, Any]]:
    stmt = select(SessionVideo).where(SessionVideo.session_id == str(session_id)).order_by(SessionVideo.created_at.desc())
    return [video_to_dict(row) for row in db.scalars(stmt).all()]

def get_session_video(db: Session, video_id: str) -> SessionVideo | None:
    return db.get(SessionVideo, str(video_id))

def create_session_video(db: Session, **kwargs) -> dict[str, Any]:
    row = SessionVideo(id=str(uuid4()), source="Onform", **kwargs)
    db.add(row); db.commit(); db.refresh(row)
    return video_to_dict(row)

def delete_session_video(db: Session, video_id: str) -> bool:
    row = db.get(SessionVideo, str(video_id))
    if row is None: return False
    path = VIDEO_ROOT / row.stored_filename
    db.delete(row); db.commit()
    if path.exists(): path.unlink()
    return True

def safe_video_path(stored_filename: str) -> Path:
    candidate = (VIDEO_ROOT / stored_filename).resolve()
    root = VIDEO_ROOT.resolve()
    if root not in candidate.parents and candidate != root:
        raise ValueError("Invalid video path")
    return candidate
