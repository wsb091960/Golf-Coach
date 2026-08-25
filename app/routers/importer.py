from __future__ import annotations
import csv, hashlib, io, re
from collections import Counter
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.store import add_shot, get_session, get_student, list_sessions, shot_signature_exists, update_session

APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
router = APIRouter(prefix="/imports/garmin", tags=["Garmin R10"])

ALIASES = {
    "club": ["clubtype","clubname","club"],
    "shot_shape": ["shotshape","shape","ballflight","ballflightshape","flightshape"],
    "ball_speed": ["ballspeed","ballspeedmph"],
    "club_speed": ["clubspeed","clubheadspeed","clubspeedmph"],
    "smash_factor": ["smashfactor","smash"],
    "launch_angle": ["launchangle","verticallaunchangle"],
    "launch_direction": ["launchdirection","horizontallaunchangle","startdirection"],
    "spin_rate": ["spinrate","totalspin","spinrpm"],
    "spin_axis": ["spinaxis","spinaxisangle"],
    "carry_distance": ["carrydistance","carry","carryyards","carryyds"],
    "total_distance": ["totaldistance","total","totalyards","totalyds"],
    "attack_angle": ["attackangle","angleofattack","aoa"],
    "club_path": ["clubpath","swingpath","path"],
    "club_face": ["clubface","faceangle","faceangleattarget"],
    "face_to_path": ["facetopath","facepath"],
    "apex_height": ["apexheight","apex","maximumheight"],
    "offline_distance": ["carrydeviationdistance","offlinedistance","offline","lateraldistance","carrydeviation"],
}
NUMERIC_FIELDS = set(ALIASES) - {"club","shot_shape"}

def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]","",str(value).lower().strip())

def parse_number(value: Any) -> float | None:
    if value is None: return None
    text = str(value).strip().replace(",","")
    if not text: return None
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", text)
    if not match: return None
    try: return round(float(match.group()),4)
    except ValueError: return None

def identify_columns(fieldnames: list[str]) -> dict[str,str]:
    normalized = {normalize_header(n): n for n in fieldnames if n}
    mapping = {}
    for internal, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[internal] = normalized[alias]
                break
    return mapping

def derive_shot_shape(shot: dict[str,Any], handedness: str="Unknown") -> str:
    explicit = str(shot.get("shot_shape") or "").strip()
    if explicit:
        return explicit
    ftp = shot.get("face_to_path")
    if ftp is None and shot.get("club_face") is not None and shot.get("club_path") is not None:
        ftp = float(shot["club_face"]) - float(shot["club_path"])
    curve_direction = "Straight"
    curve_amount = 0.0
    if ftp is not None:
        curve_amount = float(ftp)
        if abs(curve_amount) > 1.0:
            curve_direction = "Left" if curve_amount < 0 else "Right"
    elif shot.get("spin_axis") is not None:
        curve_amount = float(shot["spin_axis"])
        if abs(curve_amount) > 2.0:
            curve_direction = "Left" if curve_amount < 0 else "Right"

    start_value = shot.get("launch_direction")
    if start_value is None and shot.get("club_face") is not None:
        start_value = shot.get("club_face")
    start_label = ""
    if start_value is not None:
        start = float(start_value)
        if start < -1.0:
            start_label = "Pull"
        elif start > 1.0:
            start_label = "Push"

    handedness = str(handedness or "Unknown").title()
    if handedness not in {"Right", "Left"}:
        if curve_direction == "Straight":
            return f"{start_label} Straight".strip() or "Straight"
        return f"{start_label} {curve_direction} Curve".strip()
    if curve_direction == "Straight":
        return f"{start_label} Straight".strip() or "Straight"

    strong_curve = abs(curve_amount) >= 4.0
    draw_side = "Left" if handedness == "Right" else "Right"
    if curve_direction == draw_side:
        curve_name = "Hook" if strong_curve else "Draw"
    else:
        curve_name = "Slice" if strong_curve else "Fade"
    return f"{start_label} {curve_name}".strip()

def make_signature(shot: dict[str,Any]) -> str:
    fields = ["club","ball_speed","club_speed","carry_distance","total_distance","launch_angle","spin_rate","club_path","club_face"]
    raw = "|".join(str(shot.get(k) if shot.get(k) is not None else "") for k in fields)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def session_choices(db: Session) -> list[dict[str,Any]]:
    choices = []
    for session in list_sessions(db=db, limit=1000):
        student = get_student(str(session.get("student_id","")), db=db)
        choices.append({**session, "student_name": student.get("name") if student else "Unknown Student"})
    return choices

@router.get("", response_class=HTMLResponse, name="garmin_import")
def garmin_import_page(request: Request, session_id: str="", imported: int=0, duplicates: int=0, db: Session=Depends(get_db)):
    return templates.TemplateResponse(request=request, name="garmin_import.html", context={
        "page_title":"Garmin R10 Import","active_page":"garmin","sessions":session_choices(db),
        "selected_session_id":session_id,"imported":imported,"duplicates":duplicates,
    })

@router.post("", name="garmin_import_upload")
async def garmin_import_upload(session_id: str=Form(...), csv_file: UploadFile=File(...), db: Session=Depends(get_db)):
    session = get_session(session_id, db=db)
    if session is None: raise HTTPException(status_code=400, detail="Selected session was not found.")
    if not (csv_file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a Garmin CSV file.")
    raw = await csv_file.read()
    if not raw: raise HTTPException(status_code=400, detail="The uploaded CSV is empty.")
    text = None
    for enc in ("utf-8-sig","utf-8","latin-1"):
        try:
            text = raw.decode(enc); break
        except UnicodeDecodeError:
            pass
    if text is None: raise HTTPException(status_code=400, detail="Could not decode the CSV file.")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    mapping = identify_columns([str(n) for n in (reader.fieldnames or []) if n])
    if not mapping:
        raise HTTPException(status_code=400, detail="No recognized Garmin R10 shot-data columns were found.")
    imported = duplicates = 0
    imported_clubs: list[str] = []
    student = get_student(str(session.get("student_id", "")), db=db)
    handedness = student.get("handedness", "Unknown") if student else "Unknown"
    for row in reader:
        shot = {"session_id":session_id,"student_id":str(session.get("student_id","")),"source":"Garmin R10"}
        populated = 0
        for internal in ALIASES:
            source = mapping.get(internal)
            if not source:
                shot[internal] = None; continue
            raw_value = row.get(source)
            value = parse_number(raw_value) if internal in NUMERIC_FIELDS else str(raw_value or "").strip()
            shot[internal] = value
            if value not in (None,""): populated += 1
        if populated < 2: continue
        if shot.get("face_to_path") is None and shot.get("club_face") is not None and shot.get("club_path") is not None:
            shot["face_to_path"] = round(float(shot["club_face"]) - float(shot["club_path"]),4)
        shot["shot_shape"] = derive_shot_shape(shot, handedness)
        signature = make_signature(shot)
        if shot_signature_exists(session_id, signature, db=db):
            duplicates += 1; continue
        shot["raw_signature"] = signature
        add_shot(shot, db=db)
        if shot.get("club"):
            imported_clubs.append(str(shot["club"]))
        imported += 1
    if imported_clubs:
        primary_club = Counter(imported_clubs).most_common(1)[0][0]
        update_session(session_id, {"primary_club": primary_club}, db=db)
    return RedirectResponse(url=f"/imports/garmin?session_id={session_id}&imported={imported}&duplicates={duplicates}", status_code=303)
