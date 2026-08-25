"""
WSBCO Golf Coach
Coaching Analysis
Phase 2.1.3 — Attack Angle + Shot Shape
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.store import list_shots

APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(
    directory=str(APP_DIR / "templates")
)

router = APIRouter(
    prefix="/analysis",
    tags=["Coaching Analysis"],
)


def average(
    rows: list[dict[str, Any]],
    field: str,
) -> float | None:
    values: list[float] = []

    for row in rows:
        if not row.get("included", True):
            continue

        value = row.get(field)

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


def shape_summary(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    included_rows = [
        row
        for row in rows
        if row.get("included", True)
    ]

    counts = Counter(
        str(
            row.get("shot_shape")
            or "Unknown"
        )
        for row in included_rows
    )

    total = sum(counts.values())

    dominant_shape = (
        counts.most_common(1)[0][0]
        if counts
        else "Unknown"
    )

    distribution = []

    for shape, count in counts.most_common():
        pct = (
            round(
                (count / total) * 100,
                1,
            )
            if total
            else 0.0
        )

        distribution.append(
            {
                "shape": shape,
                "count": count,
                "pct": pct,
            }
        )

    return {
        "dominant_shape": dominant_shape,
        "distribution": distribution,
    }


@router.get(
    "",
    response_class=HTMLResponse,
    name="analysis_page",
)
def analysis_page(
    request: Request,
    db: Session = Depends(get_db),
):
    shots = list_shots(
        db=db,
        limit=10000,
    )

    included_shots = [
        shot
        for shot in shots
        if shot.get("included", True)
    ]

    groups: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for shot in shots:
        club = (
            shot.get("club")
            or "Unknown"
        )

        groups[str(club)].append(
            shot
        )

    club_rows = []

    for club, club_shots in groups.items():
        included_club_shots = [
            row
            for row in club_shots
            if row.get("included", True)
        ]

        shapes = shape_summary(
            club_shots
        )

        club_rows.append(
            {
                "club": club,
                "shots": len(
                    included_club_shots
                ),
                "carry": average(
                    club_shots,
                    "carry_distance",
                ),
                "ball_speed": average(
                    club_shots,
                    "ball_speed",
                ),
                "club_speed": average(
                    club_shots,
                    "club_speed",
                ),
                "smash": average(
                    club_shots,
                    "smash_factor",
                ),
                "attack": average(
                    club_shots,
                    "attack_angle",
                ),
                "path": average(
                    club_shots,
                    "club_path",
                ),
                "face": average(
                    club_shots,
                    "club_face",
                ),
                "face_to_path": average(
                    club_shots,
                    "face_to_path",
                ),
                "dominant_shape": (
                    shapes[
                        "dominant_shape"
                    ]
                ),
            }
        )

    club_rows.sort(
        key=lambda row: row["shots"],
        reverse=True,
    )

    overall_shapes = shape_summary(
        shots
    )

    return templates.TemplateResponse(
        request=request,
        name="analysis.html",
        context={
            "page_title": "Coaching Analysis",
            "active_page": "analysis",
            "total_shots": len(
                included_shots
            ),
            "club_rows": club_rows,
            "dominant_shape": (
                overall_shapes[
                    "dominant_shape"
                ]
            ),
            "shape_distribution": (
                overall_shapes[
                    "distribution"
                ]
            ),
            "average_attack": average(
                shots,
                "attack_angle",
            ),
        },
    )
