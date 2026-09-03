from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.store import get_session
from app.video_store import (
    ALLOWED_EXTENSIONS,
    MAX_VIDEO_BYTES,
    VIDEO_ROOT,
    create_session_video,
    delete_session_video,
    get_session_video,
    safe_video_path,
)


router = APIRouter(
    prefix="/sessions",
    tags=["Session Videos"],
)


# ============================================================
# HELPERS
# ============================================================

CHUNK_BYTES = 512 * 1024
CHUNK_ROOT = VIDEO_ROOT / ".chunk_uploads"


def _require_session(session_id: str, db: Session):
    coaching_session = get_session(session_id, db=db)

    if coaching_session is None:
        raise HTTPException(404, "Session not found")

    return coaching_session


def _student_id_from_session(coaching_session) -> str:
    if isinstance(coaching_session, dict):
        return str(coaching_session.get("student_id", ""))

    return str(getattr(coaching_session, "student_id", ""))


def _parse_shot_number(value: str | None) -> int | None:
    text = str(value or "").strip()

    if not text:
        return None

    try:
        return int(text)
    except ValueError:
        return None


def _clean_upload_name(
    filename: str | None,
    fallback: str = "swing-video.mp4",
) -> tuple[str, str]:
    original = Path(filename or fallback).name
    ext = Path(original).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            "Use MP4, MOV, M4V, or WEBM",
        )

    return original, ext


async def _save_upload_file(
    session_id: str,
    video_file: UploadFile,
) -> tuple[str, str]:
    original, ext = _clean_upload_name(
        video_file.filename,
    )

    content = await video_file.read()

    if not content:
        raise HTTPException(
            400,
            "Video file is empty",
        )

    if len(content) > MAX_VIDEO_BYTES:
        raise HTTPException(
            413,
            "Video exceeds 750 MB",
        )

    stored = f"{session_id}_{uuid4().hex}{ext}"
    destination = VIDEO_ROOT / stored

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_bytes(content)

    return original, stored


def _remove_saved_file(stored_filename: str) -> None:
    if not stored_filename:
        return

    path = VIDEO_ROOT / stored_filename

    if path.exists():
        path.unlink()


def _require_original_video(
    db: Session,
    session_id: str,
    video_id: str,
):
    row = get_session_video(
        db,
        video_id,
    )

    if row is None or row.session_id != str(session_id):
        raise HTTPException(
            404,
            "Original swing not found",
        )

    if row.video_type != "original_swing":
        raise HTTPException(
            400,
            "Onform analysis must be linked to an Original Swing",
        )

    return row


def _chunk_directory(upload_id: str) -> Path:
    try:
        clean = UUID(str(upload_id)).hex
    except (ValueError, AttributeError):
        raise HTTPException(
            400,
            "Invalid upload identifier",
        )

    path = (CHUNK_ROOT / clean).resolve()
    root = CHUNK_ROOT.resolve()

    if root not in path.parents:
        raise HTTPException(
            400,
            "Invalid upload path",
        )

    return path


# ============================================================
# ORIGINAL SWING UPLOAD
# ============================================================

@router.post(
    "/{session_id}/videos",
    name="session_video_upload",
)
async def upload_original_swing(
    session_id: str,
    video_file: UploadFile = File(...),
    title: str = Form("Swing Video"),
    camera_view: str = Form(""),
    club: str = Form(""),
    shot_number: str = Form(""),
    notes: str = Form(""),
    onform_url: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    Upload a raw/original swing.

    This route ALWAYS creates video_type='original_swing'.
    It never creates an Onform analysis.
    """

    coaching_session = _require_session(
        session_id,
        db,
    )

    original, stored = await _save_upload_file(
        session_id,
        video_file,
    )

    try:
        create_session_video(
            db,
            session_id=str(session_id),
            student_id=_student_id_from_session(
                coaching_session
            ),
            title=title.strip() or "Swing Video",
            camera_view=camera_view.strip(),
            club=club.strip(),
            shot_number=_parse_shot_number(
                shot_number
            ),
            notes=notes.strip(),
            original_filename=original,
            stored_filename=stored,
            content_type=(
                video_file.content_type
                or "video/mp4"
            ),
            source="Golf Coach",
            onform_url=onform_url.strip(),
            video_type="original_swing",
            parent_video_id=None,
            onform_processed=False,
            analysis_status="not_analyzed",
        )

    except Exception:
        _remove_saved_file(stored)
        raise

    return RedirectResponse(
        f"/sessions/{session_id}?video_added=1",
        status_code=303,
    )


# ============================================================
# DEDICATED ONFORM ANALYSIS UPLOAD
# ============================================================

@router.post(
    "/{session_id}/videos/{parent_video_id}/onform-analysis",
    name="session_onform_analysis_upload",
)
async def upload_onform_analysis(
    session_id: str,
    parent_video_id: str,
    video_file: UploadFile = File(...),
    title: str = Form("Onform Analysis"),
    camera_view: str = Form(""),
    club: str = Form(""),
    shot_number: str = Form(""),
    notes: str = Form(""),
    onform_url: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    Import a completed/exported Onform analysis.

    The parent swing ID is part of the URL, so this route
    ALWAYS creates video_type='onform_analysis' and ALWAYS
    links it to a validated Original Swing.
    """

    coaching_session = _require_session(
        session_id,
        db,
    )

    parent = _require_original_video(
        db,
        session_id,
        parent_video_id,
    )

    original, stored = await _save_upload_file(
        session_id,
        video_file,
    )

    try:
        create_session_video(
            db,
            session_id=str(session_id),
            student_id=_student_id_from_session(
                coaching_session
            ),
            title=title.strip() or "Onform Analysis",
            camera_view=(
                camera_view.strip()
                or parent.camera_view
                or ""
            ),
            club=(
                club.strip()
                or parent.club
                or ""
            ),
            shot_number=(
                _parse_shot_number(shot_number)
                if str(shot_number or "").strip()
                else parent.shot_number
            ),
            notes=notes.strip(),
            original_filename=original,
            stored_filename=stored,
            content_type=(
                video_file.content_type
                or "video/mp4"
            ),
            source="Onform",
            onform_url=onform_url.strip(),
            video_type="onform_analysis",
            parent_video_id=str(parent.id),
            onform_processed=True,
            analysis_status="analyzed",
        )

    except Exception:
        _remove_saved_file(stored)
        raise

    return RedirectResponse(
        f"/sessions/{session_id}?onform_analysis_added=1",
        status_code=303,
    )


# ============================================================
# STREAM
# ============================================================

@router.get(
    "/{session_id}/videos/{video_id}/stream",
    name="session_video_stream",
)
def stream_session_video(
    session_id: str,
    video_id: str,
    db: Session = Depends(get_db),
):
    row = get_session_video(
        db,
        video_id,
    )

    if row is None or row.session_id != str(session_id):
        raise HTTPException(
            404,
            "Video not found",
        )

    path = safe_video_path(
        row.stored_filename
    )

    if not path.exists():
        raise HTTPException(
            404,
            "Video file is missing",
        )

    return FileResponse(
        str(path),
        media_type=row.content_type,
        filename=row.original_filename,
        content_disposition_type="inline",
    )


# ============================================================
# DOWNLOAD
# ============================================================

@router.get(
    "/{session_id}/videos/{video_id}/download",
    name="session_video_download",
)
def download_session_video(
    session_id: str,
    video_id: str,
    db: Session = Depends(get_db),
):
    row = get_session_video(
        db,
        video_id,
    )

    if row is None or row.session_id != str(session_id):
        raise HTTPException(
            404,
            "Video not found",
        )

    path = safe_video_path(
        row.stored_filename
    )

    if not path.exists():
        raise HTTPException(
            404,
            "Video file is missing",
        )

    return FileResponse(
        str(path),
        media_type=row.content_type,
        filename=row.original_filename,
    )


# ============================================================
# DELETE
# ============================================================

@router.post(
    "/{session_id}/videos/{video_id}/delete",
    name="session_video_delete",
)
def remove_session_video(
    session_id: str,
    video_id: str,
    db: Session = Depends(get_db),
):
    row = get_session_video(
        db,
        video_id,
    )

    if row is None or row.session_id != str(session_id):
        raise HTTPException(
            404,
            "Video not found",
        )

    delete_session_video(
        db,
        video_id,
    )

    return RedirectResponse(
        f"/sessions/{session_id}",
        status_code=303,
    )


# ============================================================
# CHUNKED UPLOAD SUPPORT
# ============================================================

@router.post(
    "/{session_id}/videos/chunked/init",
    name="session_video_chunk_init",
)
def init_chunked_video(
    session_id: str,
    db: Session = Depends(get_db),
):
    _require_session(
        session_id,
        db,
    )

    CHUNK_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    upload_id = uuid4().hex
    directory = CHUNK_ROOT / upload_id

    directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    return {
        "upload_id": upload_id,
        "chunk_bytes": CHUNK_BYTES,
    }


@router.post(
    "/{session_id}/videos/chunked/{upload_id}/part/{index}",
    name="session_video_chunk",
)
async def upload_video_chunk(
    session_id: str,
    upload_id: str,
    index: int,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_session(
        session_id,
        db,
    )

    if index < 0 or index > 10000:
        raise HTTPException(
            400,
            "Invalid chunk index",
        )

    directory = _chunk_directory(
        upload_id
    )

    if not directory.exists():
        raise HTTPException(
            404,
            "Upload not found or expired",
        )

    content = await request.body()

    if not content or len(content) > CHUNK_BYTES:
        raise HTTPException(
            400,
            "Invalid video chunk",
        )

    (
        directory
        / f"{index:06d}.part"
    ).write_bytes(content)

    return {
        "received": index,
    }


@router.post(
    "/{session_id}/videos/chunked/{upload_id}/finalize",
    name="session_video_chunk_finalize",
)
async def finalize_chunked_video(
    session_id: str,
    upload_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Backward-compatible chunked upload endpoint.

    Supports:
      video_type='original_swing'
      video_type='onform_analysis' + parent_video_id
    """

    coaching_session = _require_session(
        session_id,
        db,
    )

    payload = await request.json()

    original, ext = _clean_upload_name(
        str(
            payload.get("filename")
            or "swing-video.mp4"
        )
    )

    try:
        total_chunks = int(
            payload.get(
                "total_chunks",
                0,
            )
        )
    except (TypeError, ValueError):
        raise HTTPException(
            400,
            "Invalid chunk count",
        )

    directory = _chunk_directory(
        upload_id
    )

    parts = [
        directory / f"{i:06d}.part"
        for i in range(total_chunks)
    ]

    if (
        total_chunks < 1
        or any(
            not part.exists()
            for part in parts
        )
    ):
        raise HTTPException(
            400,
            "Video upload is incomplete",
        )

    total_bytes = sum(
        part.stat().st_size
        for part in parts
    )

    if total_bytes > MAX_VIDEO_BYTES:
        raise HTTPException(
            413,
            "Video exceeds 750 MB",
        )

    stored = f"{session_id}_{uuid4().hex}{ext}"
    destination = VIDEO_ROOT / stored

    video_type = str(
        payload.get("video_type")
        or "original_swing"
    ).strip()

    parent_video_id = str(
        payload.get("parent_video_id")
        or ""
    ).strip() or None

    parent = None

    if video_type == "onform_analysis":
        if not parent_video_id:
            raise HTTPException(
                400,
                "Original swing is required for Onform analysis",
            )

        parent = _require_original_video(
            db,
            session_id,
            parent_video_id,
        )

    elif video_type != "original_swing":
        raise HTTPException(
            400,
            "Invalid video type",
        )

    try:
        with destination.open("wb") as output:
            for part in parts:
                with part.open("rb") as source:
                    while block := source.read(
                        1024 * 1024
                    ):
                        output.write(block)

        title = str(
            payload.get("title")
            or (
                "Onform Analysis"
                if video_type == "onform_analysis"
                else "Swing Video"
            )
        ).strip()

        camera_view = str(
            payload.get("camera_view")
            or ""
        ).strip()

        club = str(
            payload.get("club")
            or ""
        ).strip()

        shot_number = _parse_shot_number(
            str(
                payload.get("shot_number")
                or ""
            )
        )

        if parent is not None:
            camera_view = (
                camera_view
                or parent.camera_view
                or ""
            )

            club = (
                club
                or parent.club
                or ""
            )

            if shot_number is None:
                shot_number = parent.shot_number

        create_session_video(
            db,
            session_id=str(session_id),
            student_id=_student_id_from_session(
                coaching_session
            ),
            title=title,
            camera_view=camera_view,
            club=club,
            shot_number=shot_number,
            notes=str(
                payload.get("notes")
                or ""
            ).strip(),
            original_filename=original,
            stored_filename=stored,
            content_type=str(
                payload.get("content_type")
                or "video/mp4"
            ),
            source=(
                "Onform"
                if video_type == "onform_analysis"
                else "Golf Coach"
            ),
            onform_url=str(
                payload.get("onform_url")
                or ""
            ).strip(),
            video_type=video_type,
            parent_video_id=(
                str(parent.id)
                if parent is not None
                else None
            ),
            onform_processed=(
                video_type == "onform_analysis"
            ),
            analysis_status=(
                "analyzed"
                if video_type == "onform_analysis"
                else "not_analyzed"
            ),
        )

    except Exception:
        if destination.exists():
            destination.unlink()
        raise

    finally:
        for part in parts:
            if part.exists():
                part.unlink()

        if directory.exists():
            try:
                directory.rmdir()
            except OSError:
                pass

    return {
        "redirect_url":
            f"/sessions/{session_id}?video_added=1"
    }
