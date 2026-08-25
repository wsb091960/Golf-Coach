"""
==========================================================
WSBCO Golf Coach
Dashboard Router

File: app/routers/dashboard.py
Version: 1.2.0
==========================================================
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.store import (
    get_dashboard_summary,
    list_sessions,
    list_shots,
    list_students,
)


# ==========================================================
# PATHS / TEMPLATES / ROUTER
# ==========================================================

APP_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = APP_DIR / "templates"

templates = Jinja2Templates(
    directory=str(TEMPLATE_DIR)
)

router = APIRouter(
    tags=["Dashboard"],
)


# ==========================================================
# DASHBOARD PAGE
# ==========================================================

@router.get(
    "/",
    response_class=HTMLResponse,
    name="dashboard",
)
def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Render the main WSBCO Golf Coach dashboard.
    """

    summary = build_summary(db)
    recent_sessions = build_recent_sessions(db)
    recent_students = build_recent_students(db)
    club_summary = build_club_summary(db)

    chart_labels, chart_values = build_session_chart(
        recent_sessions=list_sessions(
            db=db,
            limit=500,
        ),
        days=30,
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page_title": "Dashboard",
            "page_heading": "Dashboard",
            "page_eyebrow": "WSBCO Golf Coach",
            "active_page": "dashboard",
            "summary": summary,
            "recent_sessions": recent_sessions,
            "recent_students": recent_students,
            "club_summary": club_summary,
            "chart_labels": chart_labels,
            "chart_values": chart_values,
        },
    )


# ==========================================================
# SUMMARY METRICS
# ==========================================================

def build_summary(
    db: Session,
) -> dict[str, Any]:
    """
    Build the summary cards displayed at the top of the dashboard.
    """

    summary = get_dashboard_summary(db)

    shot_rows = list_shots(
        db=db,
        limit=10000,
    )

    carry_values = numeric_values(
        shot_rows,
        "carry_distance",
    )

    return {
        "active_students": summary.get(
            "active_students",
            summary.get(
                "total_students",
                0,
            ),
        ),
        "total_sessions": summary.get(
            "total_sessions",
            0,
        ),
        "total_shots": summary.get(
            "total_shots",
            0,
        ),
        "average_carry": average(
            carry_values
        ),
    }


# ==========================================================
# RECENT SESSIONS
# ==========================================================

def build_recent_sessions(
    db: Session,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """
    Build recent session records for the dashboard.
    """

    session_rows = list_sessions(
        db=db,
        limit=limit,
    )

    student_rows = list_students(
        db=db,
    )

    shot_rows = list_shots(
        db=db,
    )

    student_map = {
        str(student.get("id", "")): student
        for student in student_rows
    }

    shot_counts: Counter[str] = Counter(
        str(shot.get("session_id", ""))
        for shot in shot_rows
        if shot.get("session_id")
    )

    results: list[dict[str, Any]] = []

    for golf_session in session_rows:

        session_id = str(
            golf_session.get("id", "")
        )

        student = student_map.get(
            str(
                golf_session.get(
                    "student_id",
                    "",
                )
            )
        )

        results.append(
            {
                "id": golf_session.get("id"),
                "session_date": normalize_date(
                    golf_session.get(
                        "session_date"
                    )
                ),
                "session_type": (
                    golf_session.get(
                        "session_type"
                    )
                    or "Coaching Session"
                ),
                "primary_club": (
                    golf_session.get(
                        "primary_club"
                    )
                ),
                "shot_count": shot_counts.get(
                    session_id,
                    int(
                        golf_session.get(
                            "shot_count"
                        )
                        or 0
                    ),
                ),
                "student": {
                    "id": (
                        student.get("id")
                        if student
                        else None
                    ),
                    "full_name": (
                        student_full_name(
                            student
                        )
                    ),
                },
            }
        )

    return results


# ==========================================================
# RECENT STUDENTS
# ==========================================================

def build_recent_students(
    db: Session,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """
    Build recently active student records.
    """

    student_rows = list_students(
        db=db,
        limit=limit,
    )

    results: list[dict[str, Any]] = []

    for student in student_rows:

        results.append(
            {
                "id": student.get("id"),
                "first_name": (
                    student.get(
                        "first_name"
                    )
                    or ""
                ),
                "last_name": (
                    student.get(
                        "last_name"
                    )
                    or ""
                ),
                "full_name": (
                    student_full_name(
                        student
                    )
                ),
                "handicap_index": (
                    student.get(
                        "handicap_index"
                    )
                ),
                "skill_level": (
                    student.get(
                        "skill_level"
                    )
                ),
            }
        )

    return results


# ==========================================================
# CLUB PERFORMANCE SUMMARY
# ==========================================================

def build_club_summary(
    db: Session,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """
    Aggregate shot statistics by club.
    """

    shot_rows = list_shots(
        db=db,
        limit=10000,
    )

    club_groups: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for shot in shot_rows:

        club_name = normalize_club_name(
            shot.get("club")
            or shot.get("club_name")
        )

        if not club_name:
            continue

        club_groups.setdefault(
            club_name,
            [],
        ).append(
            shot
        )

    rows: list[dict[str, Any]] = []

    for (
        club_name,
        club_shots,
    ) in club_groups.items():

        rows.append(
            {
                "club": club_name,
                "shot_count": len(
                    club_shots
                ),
                "average_carry": average(
                    numeric_values(
                        club_shots,
                        "carry_distance",
                    )
                ),
                "average_ball_speed": average(
                    numeric_values(
                        club_shots,
                        "ball_speed",
                    )
                ),
                "average_club_face": average(
                    numeric_values(
                        club_shots,
                        "club_face",
                        fallback_attribute=(
                            "face_angle"
                        ),
                    )
                ),
            }
        )

    rows.sort(
        key=lambda item: item[
            "shot_count"
        ],
        reverse=True,
    )

    return rows[:limit]


# ==========================================================
# SESSION ACTIVITY CHART
# ==========================================================

def build_session_chart(
    recent_sessions: list[Any],
    days: int = 30,
) -> tuple[
    list[str],
    list[int],
]:
    """
    Build daily session totals for the activity chart.
    """

    today = date.today()

    start_date = today - timedelta(
        days=days - 1
    )

    counts: Counter[date] = Counter()

    for golf_session in recent_sessions:

        if isinstance(
            golf_session,
            dict,
        ):
            raw_date = (
                golf_session.get(
                    "session_date"
                )
            )
        else:
            raw_date = getattr(
                golf_session,
                "session_date",
                None,
            )

        session_date = normalize_date(
            raw_date
        )

        if (
            start_date
            <= session_date
            <= today
        ):
            counts[
                session_date
            ] += 1

    labels: list[str] = []
    values: list[int] = []

    current_date = start_date

    while current_date <= today:

        labels.append(
            current_date.strftime(
                "%b %d"
            )
        )

        values.append(
            counts.get(
                current_date,
                0,
            )
        )

        current_date += timedelta(
            days=1
        )

    if not any(values):
        return [], []

    return labels, values


# ==========================================================
# HELPERS
# ==========================================================

def student_full_name(
    student: Any,
) -> str:
    """
    Return a safe display name.
    """

    if student is None:
        return "Unknown Student"

    if isinstance(
        student,
        dict,
    ):

        full_name = student.get(
            "full_name"
        )

        if full_name:
            return str(full_name)

        name = student.get(
            "name"
        )

        if name:
            return str(name)

        first_name = str(
            student.get(
                "first_name",
                "",
            )
            or ""
        ).strip()

        last_name = str(
            student.get(
                "last_name",
                "",
            )
            or ""
        ).strip()

    else:

        full_name = getattr(
            student,
            "full_name",
            None,
        )

        if full_name:
            return str(full_name)

        first_name = str(
            getattr(
                student,
                "first_name",
                "",
            )
            or ""
        ).strip()

        last_name = str(
            getattr(
                student,
                "last_name",
                "",
            )
            or ""
        ).strip()

    combined = " ".join(
        value
        for value in [
            first_name,
            last_name,
        ]
        if value
    )

    return (
        combined
        or "Unnamed Student"
    )


def normalize_date(
    value: Any,
) -> date:
    """
    Convert a value into a date.
    """

    if isinstance(
        value,
        datetime,
    ):
        return value.date()

    if isinstance(
        value,
        date,
    ):
        return value

    if isinstance(
        value,
        str,
    ):

        cleaned = value.strip()

        if cleaned:

            try:
                return datetime.fromisoformat(
                    cleaned.replace(
                        "Z",
                        "+00:00",
                    )
                ).date()

            except ValueError:
                pass

            for pattern in (
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%m/%d/%y",
                "%B %d, %Y",
            ):

                try:
                    return datetime.strptime(
                        cleaned,
                        pattern,
                    ).date()

                except ValueError:
                    continue

    return date.today()


def normalize_club_name(
    value: Any,
) -> str | None:
    """
    Standardize club names.
    """

    if value is None:
        return None

    club_name = str(
        value
    ).strip()

    if not club_name:
        return None

    replacements = {
        "DR": "Driver",
        "D": "Driver",
        "1W": "Driver",
        "3W": "3 Wood",
        "5W": "5 Wood",
        "7W": "7 Wood",
        "PW": "Pitching Wedge",
        "GW": "Gap Wedge",
        "AW": "Approach Wedge",
        "SW": "Sand Wedge",
        "LW": "Lob Wedge",
    }

    return replacements.get(
        club_name.upper(),
        club_name.title(),
    )


def numeric_values(
    records: list[Any],
    attribute: str,
    fallback_attribute: (
        str | None
    ) = None,
) -> list[float]:
    """
    Return valid numeric values.
    """

    values: list[float] = []

    for record in records:

        if isinstance(
            record,
            dict,
        ):

            value = record.get(
                attribute
            )

            if (
                value is None
                and fallback_attribute
            ):
                value = record.get(
                    fallback_attribute
                )

        else:

            value = getattr(
                record,
                attribute,
                None,
            )

            if (
                value is None
                and fallback_attribute
            ):
                value = getattr(
                    record,
                    fallback_attribute,
                    None,
                )

        if value is None:
            continue

        try:
            values.append(
                float(value)
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

    return values


def average(
    values: list[float],
) -> float | None:
    """
    Return a rounded average.
    """

    if not values:
        return None

    return round(
        sum(values)
        / len(values),
        1,
    )
