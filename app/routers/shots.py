"""
==========================================================
WSBCO Golf Coach
Shot Management Router

File: app/routers/shots.py
Version: 1.0.0
==========================================================
"""

from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ShotCreate, ShotUpdate
from app.store import (
    create_shot,
    delete_shot,
    get_session,
    get_shot,
    list_shots,
    update_shot,
)


router = APIRouter(
    prefix="/shots",
    tags=["Shots"],
)


# ==========================================================
# SHOT LIST
# ==========================================================


@router.get(
    "",
    response_class=HTMLResponse,
    name="shots_list",
)
def shots_list_page(
    request: Request,
    session_id: int | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Display shot records.

    The optional session_id query parameter limits the list
    to shots from one coaching session.
    """

    shots = list_shots(
        db=db,
        limit=5000,
    )

    if session_id is not None:
        shots = [
            shot
            for shot in shots
            if getattr(shot, "session_id", None) == session_id
        ]

    shots = sorted(
        shots,
        key=lambda shot: (
            getattr(shot, "session_id", 0) or 0,
            getattr(shot, "shot_number", 0) or 0,
            getattr(shot, "id", 0) or 0,
        ),
        reverse=True,
    )

    selected_session = None

    if session_id is not None:
        selected_session = get_session(
            db=db,
            session_id=session_id,
        )

    templates = request.app.state.templates

    return templates.TemplateResponse(
        request=request,
        name="shots/list.html",
        context={
            "page_title": "Shot Data",
            "page_heading": "Shot Data",
            "page_eyebrow": "Launch Monitor",
            "active_page": "shots",
            "shots": shots,
            "session": selected_session,
            "session_id": session_id,
            "shot_summary": build_shot_summary(shots),
        },
    )


# ==========================================================
# CREATE SHOT
# ==========================================================


@router.get(
    "/new",
    response_class=HTMLResponse,
    name="shot_new",
)
def shot_new_page(
    request: Request,
    session_id: int | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Display the manual shot-entry form.
    """

    if session_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A coaching session is required.",
        )

    session_record = require_session(
        db=db,
        session_id=session_id,
    )

    form_values = default_shot_form_values(
        session_record=session_record,
    )

    return render_shot_form(
        request=request,
        session_record=session_record,
        shot_record=None,
        form_values=form_values,
        errors={},
        form_action="/shots/new",
        submit_label="Add Shot",
        page_title="Add Shot",
    )


@router.post(
    "/new",
    response_class=HTMLResponse,
    name="shot_create",
)
def shot_create_action(
    request: Request,
    session_id: str = Form(...),
    shot_number: str | None = Form(None),
    club: str | None = Form(None),
    carry_distance: str | None = Form(None),
    total_distance: str | None = Form(None),
    ball_speed: str | None = Form(None),
    club_speed: str | None = Form(None),
    smash_factor: str | None = Form(None),
    launch_angle: str | None = Form(None),
    launch_direction: str | None = Form(None),
    spin_rate: str | None = Form(None),
    spin_axis: str | None = Form(None),
    apex_height: str | None = Form(None),
    club_path: str | None = Form(None),
    club_face: str | None = Form(None),
    face_to_path: str | None = Form(None),
    attack_angle: str | None = Form(None),
    horizontal_distance: str | None = Form(None),
    lateral_distance: str | None = Form(None),
    shot_shape: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Validate and create a manually entered shot.
    """

    form_values = build_shot_form_values(
        session_id=session_id,
        shot_number=shot_number,
        club=club,
        carry_distance=carry_distance,
        total_distance=total_distance,
        ball_speed=ball_speed,
        club_speed=club_speed,
        smash_factor=smash_factor,
        launch_angle=launch_angle,
        launch_direction=launch_direction,
        spin_rate=spin_rate,
        spin_axis=spin_axis,
        apex_height=apex_height,
        club_path=club_path,
        club_face=club_face,
        face_to_path=face_to_path,
        attack_angle=attack_angle,
        horizontal_distance=horizontal_distance,
        lateral_distance=lateral_distance,
        shot_shape=shot_shape,
        notes=notes,
    )

    errors = validate_shot_form(
        db=db,
        session_id=session_id,
        shot_number=shot_number,
        club=club,
        numeric_values={
            "carry_distance": carry_distance,
            "total_distance": total_distance,
            "ball_speed": ball_speed,
            "club_speed": club_speed,
            "smash_factor": smash_factor,
            "launch_angle": launch_angle,
            "launch_direction": launch_direction,
            "spin_rate": spin_rate,
            "spin_axis": spin_axis,
            "apex_height": apex_height,
            "club_path": club_path,
            "club_face": club_face,
            "face_to_path": face_to_path,
            "attack_angle": attack_angle,
            "horizontal_distance": horizontal_distance,
            "lateral_distance": lateral_distance,
        },
    )

    parsed_session_id = parse_optional_int(session_id)

    session_record = None

    if parsed_session_id is not None:
        session_record = get_session(
            db=db,
            session_id=parsed_session_id,
        )

    if errors:
        return render_shot_form(
            request=request,
            session_record=session_record,
            shot_record=None,
            form_values=form_values,
            errors=errors,
            form_action="/shots/new",
            submit_label="Add Shot",
            page_title="Add Shot",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    shot_data = ShotCreate(
        session_id=int(session_id),
        shot_number=parse_optional_int(shot_number),
        club=clean_optional_text(club),
        carry_distance=parse_optional_float(carry_distance),
        total_distance=parse_optional_float(total_distance),
        ball_speed=parse_optional_float(ball_speed),
        club_speed=parse_optional_float(club_speed),
        smash_factor=parse_optional_float(smash_factor),
        launch_angle=parse_optional_float(launch_angle),
        launch_direction=parse_optional_float(launch_direction),
        spin_rate=parse_optional_float(spin_rate),
        spin_axis=parse_optional_float(spin_axis),
        apex_height=parse_optional_float(apex_height),
        club_path=parse_optional_float(club_path),
        club_face=parse_optional_float(club_face),
        face_to_path=parse_optional_float(face_to_path),
        attack_angle=parse_optional_float(attack_angle),
        horizontal_distance=parse_optional_float(horizontal_distance),
        lateral_distance=parse_optional_float(lateral_distance),
        shot_shape=clean_optional_text(shot_shape),
        notes=clean_optional_text(notes),
    )

    created_shot = create_shot(
        db=db,
        shot=shot_data,
    )

    return RedirectResponse(
        url=f"/sessions/{created_shot.session_id}?shot_created=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ==========================================================
# SHOT DETAIL
# ==========================================================


@router.get(
    "/{shot_id}",
    response_class=HTMLResponse,
    name="shot_detail",
)
def shot_detail_page(
    shot_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Display one launch-monitor shot.
    """

    shot_record = require_shot(
        db=db,
        shot_id=shot_id,
    )

    templates = request.app.state.templates

    return templates.TemplateResponse(
        request=request,
        name="shots/detail.html",
        context={
            "page_title": shot_display_title(shot_record),
            "page_heading": shot_display_title(shot_record),
            "page_eyebrow": "Launch Monitor Shot",
            "active_page": "shots",
            "shot": shot_record,
            "session": getattr(shot_record, "session", None),
            "student": get_shot_student(shot_record),
            "created": request.query_params.get("created") == "1",
            "updated": request.query_params.get("updated") == "1",
        },
    )


# ==========================================================
# EDIT SHOT
# ==========================================================


@router.get(
    "/{shot_id}/edit",
    response_class=HTMLResponse,
    name="shot_edit",
)
def shot_edit_page(
    shot_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Display the edit-shot form.
    """

    shot_record = require_shot(
        db=db,
        shot_id=shot_id,
    )

    session_record = getattr(
        shot_record,
        "session",
        None,
    )

    if session_record is None:
        session_record = require_session(
            db=db,
            session_id=shot_record.session_id,
        )

    return render_shot_form(
        request=request,
        session_record=session_record,
        shot_record=shot_record,
        form_values=shot_to_form_values(shot_record),
        errors={},
        form_action=f"/shots/{shot_record.id}/edit",
        submit_label="Save Changes",
        page_title=f"Edit {shot_display_title(shot_record)}",
    )


@router.post(
    "/{shot_id}/edit",
    response_class=HTMLResponse,
    name="shot_update",
)
def shot_update_action(
    shot_id: int,
    request: Request,
    session_id: str = Form(...),
    shot_number: str | None = Form(None),
    club: str | None = Form(None),
    carry_distance: str | None = Form(None),
    total_distance: str | None = Form(None),
    ball_speed: str | None = Form(None),
    club_speed: str | None = Form(None),
    smash_factor: str | None = Form(None),
    launch_angle: str | None = Form(None),
    launch_direction: str | None = Form(None),
    spin_rate: str | None = Form(None),
    spin_axis: str | None = Form(None),
    apex_height: str | None = Form(None),
    club_path: str | None = Form(None),
    club_face: str | None = Form(None),
    face_to_path: str | None = Form(None),
    attack_angle: str | None = Form(None),
    horizontal_distance: str | None = Form(None),
    lateral_distance: str | None = Form(None),
    shot_shape: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Validate and update a shot record.
    """

    shot_record = require_shot(
        db=db,
        shot_id=shot_id,
    )

    form_values = build_shot_form_values(
        session_id=session_id,
        shot_number=shot_number,
        club=club,
        carry_distance=carry_distance,
        total_distance=total_distance,
        ball_speed=ball_speed,
        club_speed=club_speed,
        smash_factor=smash_factor,
        launch_angle=launch_angle,
        launch_direction=launch_direction,
        spin_rate=spin_rate,
        spin_axis=spin_axis,
        apex_height=apex_height,
        club_path=club_path,
        club_face=club_face,
        face_to_path=face_to_path,
        attack_angle=attack_angle,
        horizontal_distance=horizontal_distance,
        lateral_distance=lateral_distance,
        shot_shape=shot_shape,
        notes=notes,
    )

    errors = validate_shot_form(
        db=db,
        session_id=session_id,
        shot_number=shot_number,
        club=club,
        numeric_values={
            "carry_distance": carry_distance,
            "total_distance": total_distance,
            "ball_speed": ball_speed,
            "club_speed": club_speed,
            "smash_factor": smash_factor,
            "launch_angle": launch_angle,
            "launch_direction": launch_direction,
            "spin_rate": spin_rate,
            "spin_axis": spin_axis,
            "apex_height": apex_height,
            "club_path": club_path,
            "club_face": club_face,
            "face_to_path": face_to_path,
            "attack_angle": attack_angle,
            "horizontal_distance": horizontal_distance,
            "lateral_distance": lateral_distance,
        },
    )

    parsed_session_id = parse_optional_int(session_id)

    session_record = None

    if parsed_session_id is not None:
        session_record = get_session(
            db=db,
            session_id=parsed_session_id,
        )

    if errors:
        return render_shot_form(
            request=request,
            session_record=session_record,
            shot_record=shot_record,
            form_values=form_values,
            errors=errors,
            form_action=f"/shots/{shot_record.id}/edit",
            submit_label="Save Changes",
            page_title=f"Edit {shot_display_title(shot_record)}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    update_data = ShotUpdate(
        session_id=int(session_id),
        shot_number=parse_optional_int(shot_number),
        club=clean_optional_text(club),
        carry_distance=parse_optional_float(carry_distance),
        total_distance=parse_optional_float(total_distance),
        ball_speed=parse_optional_float(ball_speed),
        club_speed=parse_optional_float(club_speed),
        smash_factor=parse_optional_float(smash_factor),
        launch_angle=parse_optional_float(launch_angle),
        launch_direction=parse_optional_float(launch_direction),
        spin_rate=parse_optional_float(spin_rate),
        spin_axis=parse_optional_float(spin_axis),
        apex_height=parse_optional_float(apex_height),
        club_path=parse_optional_float(club_path),
        club_face=parse_optional_float(club_face),
        face_to_path=parse_optional_float(face_to_path),
        attack_angle=parse_optional_float(attack_angle),
        horizontal_distance=parse_optional_float(horizontal_distance),
        lateral_distance=parse_optional_float(lateral_distance),
        shot_shape=clean_optional_text(shot_shape),
        notes=clean_optional_text(notes),
    )

    updated_shot = update_shot(
        db=db,
        shot_id=shot_record.id,
        shot=update_data,
    )

    if updated_shot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shot not found.",
        )

    return RedirectResponse(
        url=f"/sessions/{updated_shot.session_id}?shot_updated=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ==========================================================
# DELETE SHOT
# ==========================================================


@router.post(
    "/{shot_id}/delete",
    name="shot_delete",
)
def shot_delete_action(
    shot_id: int,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """
    Delete one shot record.
    """

    shot_record = require_shot(
        db=db,
        shot_id=shot_id,
    )

    session_id = shot_record.session_id

    deleted = delete_shot(
        db=db,
        shot_id=shot_record.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shot not found.",
        )

    return RedirectResponse(
        url=f"/sessions/{session_id}?shot_deleted=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ==========================================================
# TEMPLATE HELPERS
# ==========================================================


def render_shot_form(
    request: Request,
    session_record: Any,
    shot_record: Any,
    form_values: dict[str, Any],
    errors: dict[str, str],
    form_action: str,
    submit_label: str,
    page_title: str,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    """
    Render the shared create/edit shot form.
    """

    templates = request.app.state.templates

    return templates.TemplateResponse(
        request=request,
        name="shots/form.html",
        context={
            "page_title": page_title,
            "page_heading": page_title,
            "page_eyebrow": "Launch Monitor",
            "active_page": "shots",
            "session": session_record,
            "shot": shot_record,
            "student": (
                getattr(session_record, "student", None)
                if session_record
                else None
            ),
            "form_values": form_values,
            "errors": errors,
            "form_action": form_action,
            "submit_label": submit_label,
            "club_options": club_options(),
            "shot_shape_options": shot_shape_options(),
        },
        status_code=status_code,
    )


def default_shot_form_values(
    session_record: Any,
) -> dict[str, Any]:
    """
    Return defaults for a new manual shot.
    """

    existing_shots = (
        getattr(session_record, "shots", None)
        or []
    )

    next_shot_number = max(
        [
            getattr(shot, "shot_number", 0) or 0
            for shot in existing_shots
        ],
        default=0,
    ) + 1

    return {
        "session_id": session_record.id,
        "shot_number": next_shot_number,
        "club": getattr(
            session_record,
            "primary_club",
            "",
        )
        or "",
        "carry_distance": "",
        "total_distance": "",
        "ball_speed": "",
        "club_speed": "",
        "smash_factor": "",
        "launch_angle": "",
        "launch_direction": "",
        "spin_rate": "",
        "spin_axis": "",
        "apex_height": "",
        "club_path": "",
        "club_face": "",
        "face_to_path": "",
        "attack_angle": "",
        "horizontal_distance": "",
        "lateral_distance": "",
        "shot_shape": "",
        "notes": "",
    }


def build_shot_form_values(
    session_id: Any,
    shot_number: Any,
    club: Any,
    carry_distance: Any,
    total_distance: Any,
    ball_speed: Any,
    club_speed: Any,
    smash_factor: Any,
    launch_angle: Any,
    launch_direction: Any,
    spin_rate: Any,
    spin_axis: Any,
    apex_height: Any,
    club_path: Any,
    club_face: Any,
    face_to_path: Any,
    attack_angle: Any,
    horizontal_distance: Any,
    lateral_distance: Any,
    shot_shape: Any,
    notes: Any,
) -> dict[str, Any]:
    """
    Preserve submitted values after validation errors.
    """

    return {
        "session_id": session_id or "",
        "shot_number": shot_number or "",
        "club": club or "",
        "carry_distance": carry_distance or "",
        "total_distance": total_distance or "",
        "ball_speed": ball_speed or "",
        "club_speed": club_speed or "",
        "smash_factor": smash_factor or "",
        "launch_angle": launch_angle or "",
        "launch_direction": launch_direction or "",
        "spin_rate": spin_rate or "",
        "spin_axis": spin_axis or "",
        "apex_height": apex_height or "",
        "club_path": club_path or "",
        "club_face": club_face or "",
        "face_to_path": face_to_path or "",
        "attack_angle": attack_angle or "",
        "horizontal_distance": horizontal_distance or "",
        "lateral_distance": lateral_distance or "",
        "shot_shape": shot_shape or "",
        "notes": notes or "",
    }


def shot_to_form_values(
    shot_record: Any,
) -> dict[str, Any]:
    """
    Convert a shot model to form-safe values.
    """

    return {
        "session_id": get_model_value(
            shot_record,
            "session_id",
        ),
        "shot_number": get_model_value(
            shot_record,
            "shot_number",
        ),
        "club": get_model_value(
            shot_record,
            "club",
        ),
        "carry_distance": get_model_value(
            shot_record,
            "carry_distance",
        ),
        "total_distance": get_model_value(
            shot_record,
            "total_distance",
        ),
        "ball_speed": get_model_value(
            shot_record,
            "ball_speed",
        ),
        "club_speed": get_model_value(
            shot_record,
            "club_speed",
        ),
        "smash_factor": get_model_value(
            shot_record,
            "smash_factor",
        ),
        "launch_angle": get_model_value(
            shot_record,
            "launch_angle",
        ),
        "launch_direction": get_model_value(
            shot_record,
            "launch_direction",
        ),
        "spin_rate": get_model_value(
            shot_record,
            "spin_rate",
        ),
        "spin_axis": get_model_value(
            shot_record,
            "spin_axis",
        ),
        "apex_height": get_model_value(
            shot_record,
            "apex_height",
        ),
        "club_path": get_model_value(
            shot_record,
            "club_path",
        ),
        "club_face": get_model_value(
            shot_record,
            "club_face",
        ),
        "face_to_path": get_model_value(
            shot_record,
            "face_to_path",
        ),
        "attack_angle": get_model_value(
            shot_record,
            "attack_angle",
        ),
        "horizontal_distance": get_model_value(
            shot_record,
            "horizontal_distance",
        ),
        "lateral_distance": get_model_value(
            shot_record,
            "lateral_distance",
        ),
        "shot_shape": get_model_value(
            shot_record,
            "shot_shape",
        ),
        "notes": get_model_value(
            shot_record,
            "notes",
        ),
    }


# ==========================================================
# VALIDATION
# ==========================================================


def validate_shot_form(
    db: Session,
    session_id: str,
    shot_number: str | None,
    club: str | None,
    numeric_values: dict[str, Any],
) -> dict[str, str]:
    """
    Validate manual shot-entry values.
    """

    errors: dict[str, str] = {}

    parsed_session_id = safe_parse_int(session_id)

    if parsed_session_id is None:
        errors["session_id"] = "A coaching session is required."
    else:
        session_record = get_session(
            db=db,
            session_id=parsed_session_id,
        )

        if session_record is None:
            errors["session_id"] = (
                "The selected coaching session could not be found."
            )

    if shot_number not in (None, ""):
        parsed_shot_number = safe_parse_int(shot_number)

        if parsed_shot_number is None:
            errors["shot_number"] = (
                "Shot number must be a whole number."
            )
        elif parsed_shot_number < 1:
            errors["shot_number"] = (
                "Shot number must be at least 1."
            )

    if not clean_optional_text(club):
        errors["club"] = "Select or enter a club."

    for field_name, value in numeric_values.items():
        if value in (None, ""):
            continue

        if safe_parse_float(value) is None:
            errors[field_name] = "Enter a valid number."

    spin_rate_value = safe_parse_float(
        numeric_values.get("spin_rate")
    )

    if spin_rate_value is not None and spin_rate_value < 0:
        errors["spin_rate"] = (
            "Spin rate cannot be negative."
        )

    smash_value = safe_parse_float(
        numeric_values.get("smash_factor")
    )

    if smash_value is not None and not 0.5 <= smash_value <= 2.0:
        errors["smash_factor"] = (
            "Smash factor must be between 0.50 and 2.00."
        )

    for distance_field in (
        "carry_distance",
        "total_distance",
        "ball_speed",
        "club_speed",
        "apex_height",
    ):
        value = safe_parse_float(
            numeric_values.get(distance_field)
        )

        if value is not None and value < 0:
            errors[distance_field] = (
                "This value cannot be negative."
            )

    return errors


# ==========================================================
# SUMMARY HELPERS
# ==========================================================


def build_shot_summary(
    shots: list[Any],
) -> dict[str, Any]:
    """
    Calculate aggregate values for a shot list.
    """

    return {
        "shot_count": len(shots),
        "average_carry": average_metric(
            shots,
            "carry_distance",
        ),
        "average_total": average_metric(
            shots,
            "total_distance",
        ),
        "average_ball_speed": average_metric(
            shots,
            "ball_speed",
        ),
        "average_club_speed": average_metric(
            shots,
            "club_speed",
        ),
        "average_smash": average_metric(
            shots,
            "smash_factor",
        ),
        "average_launch": average_metric(
            shots,
            "launch_angle",
        ),
        "average_spin": average_metric(
            shots,
            "spin_rate",
        ),
        "average_path": average_metric(
            shots,
            "club_path",
        ),
        "average_face": average_metric(
            shots,
            "club_face",
        ),
        "average_face_to_path": average_metric(
            shots,
            "face_to_path",
        ),
        "average_attack_angle": average_metric(
            shots,
            "attack_angle",
        ),
        "average_lateral": average_metric(
            shots,
            "lateral_distance",
        ),
    }


def average_metric(
    records: list[Any],
    attribute_name: str,
) -> float | None:
    """
    Calculate the average of one numeric shot field.
    """

    values: list[float] = []

    for record in records:
        value = getattr(
            record,
            attribute_name,
            None,
        )

        if value is None:
            continue

        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue

    if not values:
        return None

    return round(
        sum(values) / len(values),
        2,
    )


# ==========================================================
# MODEL HELPERS
# ==========================================================


def require_shot(
    db: Session,
    shot_id: int,
) -> Any:
    """
    Retrieve a shot or raise a 404 response.
    """

    shot_record = get_shot(
        db=db,
        shot_id=shot_id,
    )

    if shot_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shot not found.",
        )

    return shot_record


def require_session(
    db: Session,
    session_id: int,
) -> Any:
    """
    Retrieve a coaching session or raise a 404 response.
    """

    session_record = get_session(
        db=db,
        session_id=session_id,
    )

    if session_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coaching session not found.",
        )

    return session_record


def get_shot_student(
    shot_record: Any,
) -> Any:
    """
    Retrieve the student through the shot's session relationship.
    """

    session_record = getattr(
        shot_record,
        "session",
        None,
    )

    if session_record is None:
        return None

    return getattr(
        session_record,
        "student",
        None,
    )


def shot_display_title(
    shot_record: Any,
) -> str:
    """
    Return a readable shot title.
    """

    shot_number = getattr(
        shot_record,
        "shot_number",
        None,
    )

    club = clean_optional_text(
        getattr(
            shot_record,
            "club",
            None,
        )
    )

    if shot_number and club:
        return f"Shot {shot_number} — {club}"

    if shot_number:
        return f"Shot {shot_number}"

    if club:
        return f"{club} Shot"

    return f"Shot #{shot_record.id}"


def get_model_value(
    record: Any,
    attribute_name: str,
) -> Any:
    """
    Return an empty string instead of None for form fields.
    """

    value = getattr(
        record,
        attribute_name,
        None,
    )

    if value is None:
        return ""

    return value


# ==========================================================
# VALUE PARSING
# ==========================================================


def parse_optional_int(
    value: Any,
) -> int | None:
    """
    Parse an optional whole-number value.

    Raises ValueError when a non-empty invalid value is supplied.
    """

    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    return int(cleaned)


def parse_optional_float(
    value: Any,
) -> float | None:
    """
    Parse an optional decimal value.

    Raises ValueError when a non-empty invalid value is supplied.
    """

    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    return float(cleaned)


def safe_parse_int(
    value: Any,
) -> int | None:
    """
    Safely parse a whole-number value for validation.
    """

    try:
        return parse_optional_int(value)
    except (TypeError, ValueError):
        return None


def safe_parse_float(
    value: Any,
) -> float | None:
    """
    Safely parse a decimal value for validation.
    """

    try:
        return parse_optional_float(value)
    except (TypeError, ValueError):
        return None


def clean_optional_text(
    value: Any,
) -> str | None:
    """
    Trim optional text values.
    """

    if value is None:
        return None

    cleaned = str(value).strip()

    return cleaned or None


# ==========================================================
# FORM OPTIONS
# ==========================================================


def club_options() -> list[str]:
    """
    Return standard club choices.
    """

    return [
        "Driver",
        "3 Wood",
        "5 Wood",
        "7 Wood",
        "9 Wood",
        "2 Hybrid",
        "3 Hybrid",
        "4 Hybrid",
        "5 Hybrid",
        "2 Iron",
        "3 Iron",
        "4 Iron",
        "5 Iron",
        "6 Iron",
        "7 Iron",
        "8 Iron",
        "9 Iron",
        "Pitching Wedge",
        "Gap Wedge",
        "Sand Wedge",
        "Lob Wedge",
        "Putter",
        "Other",
    ]


def shot_shape_options() -> list[str]:
    """
    Return common ball-flight classifications.
    """

    return [
        "Straight",
        "Push",
        "Pull",
        "Push Draw",
        "Push Fade",
        "Pull Draw",
        "Pull Fade",
        "Draw",
        "Fade",
        "Hook",
        "Slice",
        "Block",
        "Other",
    ]