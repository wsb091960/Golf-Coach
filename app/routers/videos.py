from __future__ import annotations
from pathlib import Path
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.store import get_session
from app.video_store import ALLOWED_EXTENSIONS, MAX_VIDEO_BYTES, VIDEO_ROOT, create_session_video, delete_session_video, get_session_video, safe_video_path

router = APIRouter(prefix="/sessions", tags=["Session Videos"])

@router.post("/{session_id}/videos", name="session_video_upload")
async def upload_session_video(session_id: str, video_file: UploadFile = File(...), title: str = Form("Onform Video"), camera_view: str = Form(""), club: str = Form(""), shot_number: str = Form(""), notes: str = Form(""), onform_url: str = Form(""), db: Session = Depends(get_db)):
    session = get_session(session_id, db=db)
    if session is None: raise HTTPException(404, "Session not found")
    original = Path(video_file.filename or "onform-video.mp4").name
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS: raise HTTPException(400, "Use MP4, MOV, M4V, or WEBM")
    content = await video_file.read()
    if not content: raise HTTPException(400, "Video file is empty")
    if len(content) > MAX_VIDEO_BYTES: raise HTTPException(413, "Video exceeds 750 MB")
    stored = f"{session_id}_{uuid4().hex}{ext}"
    (VIDEO_ROOT / stored).write_bytes(content)
    sn = None
    if shot_number.strip():
        try: sn = int(shot_number.strip())
        except ValueError: pass
    create_session_video(db, session_id=session_id, student_id=str(session.get("student_id", "")), title=title.strip() or "Onform Video", camera_view=camera_view.strip(), club=club.strip(), shot_number=sn, notes=notes.strip(), original_filename=original, stored_filename=stored, content_type=video_file.content_type or "video/mp4", onform_url=onform_url.strip())
    return RedirectResponse(f"/sessions/{session_id}?video_added=1", status_code=303)

@router.get("/{session_id}/videos/{video_id}/stream", name="session_video_stream")
def stream_session_video(session_id: str, video_id: str, db: Session = Depends(get_db)):
    row = get_session_video(db, video_id)
    if row is None or row.session_id != str(session_id): raise HTTPException(404, "Video not found")
    path = safe_video_path(row.stored_filename)
    if not path.exists(): raise HTTPException(404, "Video file is missing")
    return FileResponse(str(path), media_type=row.content_type, filename=row.original_filename, content_disposition_type="inline")

@router.get("/{session_id}/videos/{video_id}/download", name="session_video_download")
def download_session_video(session_id: str, video_id: str, db: Session = Depends(get_db)):
    row = get_session_video(db, video_id)
    if row is None or row.session_id != str(session_id): raise HTTPException(404, "Video not found")
    path = safe_video_path(row.stored_filename)
    if not path.exists(): raise HTTPException(404, "Video file is missing")
    return FileResponse(str(path), media_type=row.content_type, filename=row.original_filename)

@router.post("/{session_id}/videos/{video_id}/delete", name="session_video_delete")
def remove_session_video(session_id: str, video_id: str, db: Session = Depends(get_db)):
    row = get_session_video(db, video_id)
    if row is None or row.session_id != str(session_id): raise HTTPException(404, "Video not found")
    delete_session_video(db, video_id)
    return RedirectResponse(f"/sessions/{session_id}", status_code=303)


CHUNK_BYTES = 512 * 1024
CHUNK_ROOT = VIDEO_ROOT / ".chunk_uploads"


def _chunk_directory(upload_id: str) -> Path:
    try:
        clean = UUID(str(upload_id)).hex
    except (ValueError, AttributeError):
        raise HTTPException(400, "Invalid upload identifier")
    path = (CHUNK_ROOT / clean).resolve()
    root = CHUNK_ROOT.resolve()
    if root not in path.parents:
        raise HTTPException(400, "Invalid upload path")
    return path


@router.post("/{session_id}/videos/chunked/init", name="session_video_chunk_init")
def init_chunked_video(session_id: str, db: Session = Depends(get_db)):
    if get_session(session_id, db=db) is None:
        raise HTTPException(404, "Session not found")
    upload_id = uuid4().hex
    path = CHUNK_ROOT / upload_id
    path.mkdir(parents=True, exist_ok=False)
    return {"upload_id": upload_id, "chunk_bytes": CHUNK_BYTES}


@router.post("/{session_id}/videos/chunked/{upload_id}/part/{index}", name="session_video_chunk")
async def upload_video_chunk(session_id: str, upload_id: str, index: int, request: Request, db: Session = Depends(get_db)):
    if get_session(session_id, db=db) is None:
        raise HTTPException(404, "Session not found")
    if index < 0 or index > 10000:
        raise HTTPException(400, "Invalid chunk index")
    directory = _chunk_directory(upload_id)
    if not directory.exists():
        raise HTTPException(404, "Upload not found or expired")
    content = await request.body()
    if not content or len(content) > CHUNK_BYTES:
        raise HTTPException(400, "Invalid video chunk")
    (directory / f"{index:06d}.part").write_bytes(content)
    return {"received": index}


@router.post("/{session_id}/videos/chunked/{upload_id}/finalize", name="session_video_chunk_finalize")
async def finalize_chunked_video(session_id: str, upload_id: str, request: Request, db: Session = Depends(get_db)):
    coaching_session = get_session(session_id, db=db)
    if coaching_session is None:
        raise HTTPException(404, "Session not found")
    payload = await request.json()
    original = Path(str(payload.get("filename") or "onform-video.mp4")).name
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Use MP4, MOV, M4V, or WEBM")
    try:
        total_chunks = int(payload.get("total_chunks", 0))
    except (TypeError, ValueError):
        raise HTTPException(400, "Invalid chunk count")
    directory = _chunk_directory(upload_id)
    parts = [directory / f"{i:06d}.part" for i in range(total_chunks)]
    if total_chunks < 1 or any(not part.exists() for part in parts):
        raise HTTPException(400, "Video upload is incomplete")
    total_bytes = sum(part.stat().st_size for part in parts)
    if total_bytes > MAX_VIDEO_BYTES:
        raise HTTPException(413, "Video exceeds 750 MB")
    stored = f"{session_id}_{uuid4().hex}{ext}"
    destination = VIDEO_ROOT / stored
    try:
        with destination.open("wb") as output:
            for part in parts:
                with part.open("rb") as source:
                    while block := source.read(1024 * 1024):
                        output.write(block)
        shot_number = None
        if str(payload.get("shot_number") or "").strip():
            try: shot_number = int(str(payload["shot_number"]).strip())
            except ValueError: pass
        create_session_video(
            db, session_id=session_id, student_id=str(coaching_session.get("student_id", "")),
            title=str(payload.get("title") or "Onform Video").strip() or "Onform Video",
            camera_view=str(payload.get("camera_view") or "").strip(), club=str(payload.get("club") or "").strip(),
            shot_number=shot_number, notes=str(payload.get("notes") or "").strip(), original_filename=original,
            stored_filename=stored, content_type=str(payload.get("content_type") or "video/mp4"),
            onform_url=str(payload.get("onform_url") or "").strip())
    except Exception:
        if destination.exists(): destination.unlink()
        raise
    finally:
        for part in parts:
            if part.exists(): part.unlink()
        if directory.exists(): directory.rmdir()
    return {"redirect_url": f"/sessions/{session_id}?video_added=1"}
