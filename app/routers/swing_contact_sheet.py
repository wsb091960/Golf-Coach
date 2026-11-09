"""Development-only independent swing sheet endpoint.

Requires coach-reviewed frame indices. Does not claim automatic P-position detection.
No student/session database writes. Uses decoded frames, never browser seek.
"""
from __future__ import annotations
import io
import json
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from scripts.extract_swing_contact_sheet import render
from app.services.swing_motion_candidates import propose_frames

router = APIRouter(prefix="/api/biomechanics", tags=["biomechanics"])
MAX_VIDEO_BYTES = 150 * 1024 * 1024


@router.post("/contact-sheet")
async def create_contact_sheet(
    video: UploadFile = File(...),
    frame_indices: str = Form('auto'),
    camera_angle: str = Form(...),
    output_format: str = Form('zip'),
):
    if output_format not in ("zip", "png"):
        raise HTTPException(422, "output_format must be zip or png")
    if camera_angle not in ("fo", "dtl"):
        raise HTTPException(422, "camera_angle must be fo or dtl")
    if Path(video.filename or "").suffix.lower() not in (".mp4", ".mov", ".m4v"):
        raise HTTPException(422, "Only MP4, MOV, and M4V videos are supported")
    automatic = frame_indices.strip().lower() == "auto"
    indices = None
    if not automatic:
        try:
            indices = [int(x.strip()) for x in frame_indices.split(",")]
        except ValueError:
            raise HTTPException(422, "Provide ten frame indices or auto")
        if len(indices) != 10 or any(x < 0 for x in indices) or indices != sorted(set(indices)):
            raise HTTPException(422, "Ten unique ascending nonnegative frame indices required")

    with tempfile.TemporaryDirectory(prefix="wsbco-swing-") as folder:
        base = Path(folder)
        video_path = base / ("swing" + Path(video.filename or "").suffix.lower())
        size = 0
        try:
            with video_path.open("wb") as dest:
                while chunk := await video.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_VIDEO_BYTES:
                        raise HTTPException(413, "Video exceeds 150 MB limit")
                    dest.write(chunk)
            if not size:
                raise HTTPException(422, "Video is empty")
            if automatic:
                try:
                    indices = await run_in_threadpool(propose_frames, video_path)
                except (ValueError, RuntimeError) as exc:
                    raise HTTPException(422, str(exc))
            output = base / f"{camera_angle}_p1_p10.png"
            try:
                await run_in_threadpool(render, video_path, indices, output)
            except (ValueError, RuntimeError) as exc:
                raise HTTPException(422, str(exc))
            if output_format == "png":
                return Response(output.read_bytes(), media_type="image/png", headers={"Cache-Control": "no-store"})
            manifest = json.loads(output.with_suffix(".json").read_text())
            manifest["camera_angle"] = camera_angle
            manifest["selection_method"] = "motion_window_provisional" if automatic else "manual_indices"
            manifest["warning"] = "These are NOT verified P1-P10 detections. Coach must correct and approve."
            manifest["video"] = Path(video.filename or "").name
            with io.BytesIO() as archive:
                with ZipFile(archive, "w", ZIP_DEFLATED) as z:
                    z.writestr(output.name, output.read_bytes())
                    z.writestr("checkpoints.json", json.dumps(manifest, indent=2))
                return Response(
                    archive.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="WSBCO_{camera_angle}_P1-P10.zip"',
                             "Cache-Control": "no-store"},
                )
        finally:
            await video.close()
