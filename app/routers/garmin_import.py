"""Garmin Approach R10 CSV importer for WSBCO Golf Coach.

Drop this file into app/routers/garmin_import.py.
The module previews and validates a CSV before adding shots to app.store.shots.
"""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.store import pending_imports, sessions, shots, students


APP_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

router = APIRouter(prefix="/imports/garmin", tags=["Garmin R10"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "shot_date": ("date", "shotdate", "datetime", "timestamp", "time"),
    "club": ("club", "clubname", "clubtype"),
    "ball_speed": ("ballspeed", "ballspeedmph", "ballvelocity"),
    "club_speed": (
        "clubspeed",
        "clubheadspeed",
        "clubspeedmph",
        "clubheadspeedmph",
    ),
    "smash_factor": ("smashfactor", "smash"),
    "launch_angle": ("launchangle", "verticallaunchangle", "vla"),
    "launch_direction": (
        "launchdirection",
        "horizontallaunchangle",
        "startdirection",
        "startline",
    ),
    "spin_rate": ("spinrate", "totalspin", "backspin", "spinrpm"),
    "spin_axis": ("spinaxis", "spinaxisangle"),
    "carry_distance": (
        "carrydistance",
        "carry",
        "carryyards",
        "carryyds",
    ),
    "total_distance": (
        "totaldistance",
        "total",
        "totalyards",
        "totalyds",
    ),
    "apex_height": (
        "apexheight",
        "apex",
        "maximumheight",
        "maxheight",
    ),
    "descent_angle": ("descentangle", "landingangle"),
    "attack_angle": ("attackangle", "angleofattack", "aoa"),
    "club_path": ("clubpath", "swingpath", "path"),
    "club_face": (
        "clubface",
        "faceangle",
        "faceangleattarget",
        "face",
    ),
    "face_to_path": ("facetopath", "facepath"),
    "dynamic_loft": ("dynamicloft", "deliveredloft"),
    "offline_distance": (
        "offlinedistance",
        "offline",
        "lateral",
        "lateraldistance",
        "sidedistance",
    ),
}

NUMERIC_FIELDS = set(COLUMN_ALIASES) - {"shot_date", "club"}

DISPLAY_FIELDS = [
    ("club", "Club"),
    ("ball_speed", "Ball Speed"),
    ("club_speed", "Club Speed"),
    ("smash_factor", "Smash"),
    ("launch_angle", "Launch Angle"),
    ("launch_direction", "Launch Direction"),
    ("spin_rate", "Spin Rate"),
    ("carry_distance", "Carry"),
    ("total_distance", "Total"),
    ("club_path", "Club Path"),
    ("club_face", "Club Face"),
    ("face_to_path", "Face-to-Path"),
    ("attack_angle", "Attack Angle"),
]


def normalize_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower().strip())


def parse_number(value: object) -> float | None:
    """Parse Garmin numeric values while preserving signed measurements."""
    if value is None:
        return None

    text = str(value).strip().replace("\u00a0", " ")
    if not text or text.lower() in {"n/a", "na", "null", "none", "--"}:
        return None

    # Handle decimal comma when there is no decimal point: 12,5 -> 12.5.
    if re.fullmatch(r"[-+]?\d+,\d+", text):
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")

    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", text)
    if not match:
        return None

    try:
        return round(float(match.group(0)), 3)
    except ValueError:
        return None


def find_student(student_id: str) -> dict:
    for student in students:
        if str(student.get("id")) == str(student_id):
            return student
    raise HTTPException(status_code=404, detail="Student not found.")


def find_session(session_id: str) -> dict:
    for coaching_session in sessions:
        if str(coaching_session.get("id")) == str(session_id):
            return coaching_session
    raise HTTPException(status_code=404, detail="Session not found.")


def student_name(student_id: str) -> str:
    student = find_student(student_id)
    return f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()


def session_choices() -> list[dict]:
    choices = []
    for coaching_session in sessions:
        choices.append(
            {
                "id": coaching_session.get("id"),
                "student_id": coaching_session.get("student_id"),
                "student_name": student_name(coaching_session.get("student_id")),
                "session_date": coaching_session.get("session_date", ""),
                "session_type": coaching_session.get("session_type", "Practice"),
            }
        )
    return sorted(choices, key=lambda row: row["session_date"], reverse=True)


def identify_columns(fieldnames: list[str]) -> tuple[dict[str, str], list[str]]:
    normalized_to_original = {
        normalize_header(name): name for name in fieldnames if name
    }
    column_map: dict[str, str] = {}

    for internal_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized_to_original:
                column_map[internal_name] = normalized_to_original[alias]
                break

    recognized = set(column_map.values())
    ignored = [name for name in fieldnames if name and name not in recognized]
    return column_map, ignored


def normalize_row(raw_row: dict, column_map: dict[str, str], row_number: int) -> dict:
    shot: dict = {"preview_row": row_number}
    for internal_name in COLUMN_ALIASES:
        source = column_map.get(internal_name)
        raw_value = raw_row.get(source) if source else None
        if internal_name in NUMERIC_FIELDS:
            shot[internal_name] = parse_number(raw_value)
        else:
            text = str(raw_value or "").strip()
            shot[internal_name] = text or None
    return shot


def row_has_shot_data(shot: dict) -> bool:
    metric_fields = (
        "ball_speed",
        "club_speed",
        "carry_distance",
        "total_distance",
        "launch_angle",
        "spin_rate",
        "club_path",
        "club_face",
    )
    metric_count = sum(shot.get(field) is not None for field in metric_fields)
    return bool(shot.get("club")) or metric_count >= 2


def average(rows: list[dict], field_name: str) -> float | None:
    values = [row[field_name] for row in rows if row.get(field_name) is not None]
    return round(sum(values) / len(values), 1) if values else None


def calculate_summary(rows: list[dict]) -> dict:
    club_counts = Counter((row.get("club") or "Unknown").strip() for row in rows)
    return {
        "shot_count": len(rows),
        "club_counts": sorted(club_counts.items(), key=lambda item: (-item[1], item[0])),
        "average_ball_speed": average(rows, "ball_speed"),
        "average_club_speed": average(rows, "club_speed"),
        "average_smash": average(rows, "smash_factor"),
        "average_carry": average(rows, "carry_distance"),
        "average_total": average(rows, "total_distance"),
        "average_launch": average(rows, "launch_angle"),
        "average_spin": average(rows, "spin_rate"),
        "average_path": average(rows, "club_path"),
        "average_face": average(rows, "club_face"),
        "average_face_to_path": average(rows, "face_to_path"),
    }


def decode_csv(file_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="The CSV encoding could not be read.")


def build_reader(decoded_text: str) -> csv.DictReader:
    sample = decoded_text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return csv.DictReader(io.StringIO(decoded_text), dialect=dialect)


def page_context(**extra: object) -> dict:
    return {
        "app_name": "WSBCO Golf Coach",
        "page_title": "Garmin R10 Import",
        "sessions": session_choices(),
        "selected_session": None,
        "preview": None,
        "display_fields": DISPLAY_FIELDS,
        "error": None,
        **extra,
    }


@router.get("", response_class=HTMLResponse)
async def garmin_import_page(request: Request, session_id: str = ""):
    selected_session = find_session(session_id) if session_id else None
    return templates.TemplateResponse(
        request=request,
        name="garmin_import.html",
        context=page_context(selected_session=selected_session),
    )


@router.post("/preview", response_class=HTMLResponse)
async def preview_garmin_csv(
    request: Request,
    session_id: str = Form(...),
    csv_file: UploadFile = File(...),
):
    coaching_session = find_session(session_id)
    student = find_student(coaching_session["student_id"])
    filename = csv_file.filename or "Garmin R10.csv"

    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    file_bytes = await csv_file.read(MAX_UPLOAD_BYTES + 1)
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The CSV exceeds the 5 MB limit.")

    reader = build_reader(decode_csv(file_bytes))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="No CSV headers were found.")

    column_map, ignored_headers = identify_columns(reader.fieldnames)
    required_signal = {"club", "ball_speed", "club_speed", "carry_distance", "total_distance"}
    if not column_map or not (required_signal & set(column_map)):
        raise HTTPException(
            status_code=400,
            detail="No recognizable Garmin R10 shot-data columns were found.",
        )

    valid_rows: list[dict] = []
    rejected_rows: list[int] = []
    for row_number, raw_row in enumerate(reader, start=2):
        normalized = normalize_row(raw_row, column_map, row_number)
        if row_has_shot_data(normalized):
            valid_rows.append(normalized)
        else:
            rejected_rows.append(row_number)

    if not valid_rows:
        raise HTTPException(status_code=400, detail="The CSV contains no usable shot rows.")

    import_token = str(uuid4())
    preview = {
        "token": import_token,
        "filename": filename,
        "session_id": session_id,
        "student_id": student["id"],
        "student_name": f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
        "session_date": coaching_session.get("session_date", ""),
        "session_type": coaching_session.get("session_type", "Practice"),
        "rows": valid_rows,
        "summary": calculate_summary(valid_rows),
        "column_map": column_map,
        "ignored_headers": ignored_headers,
        "rejected_rows": rejected_rows,
        "created_at": datetime.now().isoformat(),
    }
    pending_imports[import_token] = preview

    return templates.TemplateResponse(
        request=request,
        name="garmin_import.html",
        context=page_context(selected_session=coaching_session, preview=preview),
    )


@router.post("/confirm")
async def confirm_garmin_import(import_token: str = Form(...)):
    preview = pending_imports.get(import_token)
    if not preview:
        raise HTTPException(
            status_code=404,
            detail="The import preview expired. Upload the CSV again.",
        )

    coaching_session = find_session(preview["session_id"])
    imported_at = datetime.now()
    existing_count = sum(
        1 for item in shots if item.get("session_id") == coaching_session["id"]
    )

    for offset, row in enumerate(preview["rows"], start=1):
        shot = {
            "id": str(uuid4()),
            "student_id": preview["student_id"],
            "session_id": preview["session_id"],
            "shot_number": existing_count + offset,
            "source": "Garmin R10",
            "source_filename": preview["filename"],
            "imported_at": imported_at.strftime("%B %d, %Y at %I:%M %p"),
            "imported_at_iso": imported_at.isoformat(),
            "included": True,
        }
        for field_name in COLUMN_ALIASES:
            shot[field_name] = row.get(field_name)
        shots.append(shot)

    coaching_session["shot_count"] = sum(
        1 for item in shots if item.get("session_id") == coaching_session["id"]
    )
    coaching_session["updated_at"] = imported_at.strftime("%B %d, %Y at %I:%M %p")
    coaching_session["updated_at_iso"] = imported_at.isoformat()

    del pending_imports[import_token]
    return RedirectResponse(
        url=f"/sessions/{coaching_session['id']}?imported=1",
        status_code=303,
    )


@router.post("/cancel")
async def cancel_garmin_import(import_token: str = Form(...)):
    pending_imports.pop(import_token, None)
    return RedirectResponse(url="/imports/garmin", status_code=303)
