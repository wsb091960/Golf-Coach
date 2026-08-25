from __future__ import annotations

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Shot, Student


DERIVED_LABELS = {
    "",
    "Unknown",
    "Straight",
    "Left Curve",
    "Right Curve",
    "Pull Straight",
    "Push Straight",
    "Pull Left Curve",
    "Pull Right Curve",
    "Push Left Curve",
    "Push Right Curve",
}


def classify(shot: Shot, handedness: str) -> str:
    ftp = shot.face_to_path

    if ftp is None and shot.club_face is not None and shot.club_path is not None:
        ftp = shot.club_face - shot.club_path

    curve_direction = "Straight"
    curve_amount = 0.0

    if ftp is not None:
        curve_amount = float(ftp)
        if abs(curve_amount) <= 1.0:
            curve_direction = "Straight"
        elif curve_amount < 0:
            curve_direction = "Left"
        else:
            curve_direction = "Right"
    elif shot.spin_axis is not None:
        curve_amount = float(shot.spin_axis)
        if abs(curve_amount) <= 2.0:
            curve_direction = "Straight"
        elif curve_amount < 0:
            curve_direction = "Left"
        else:
            curve_direction = "Right"

    start_value = (
        shot.launch_direction
        if shot.launch_direction is not None
        else shot.club_face
    )

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

    if handedness == "Right":
        if curve_direction == "Left":
            curve_name = "Hook" if strong_curve else "Draw"
        else:
            curve_name = "Slice" if strong_curve else "Fade"
    else:
        if curve_direction == "Right":
            curve_name = "Hook" if strong_curve else "Draw"
        else:
            curve_name = "Slice" if strong_curve else "Fade"

    return f"{start_label} {curve_name}".strip()


def main() -> None:
    db = SessionLocal()

    try:
        students = {
            student.id: student
            for student in db.scalars(select(Student)).all()
        }

        shots = db.scalars(select(Shot)).all()

        updated = 0
        preserved = 0
        unknown_hand = 0

        for shot in shots:
            current = str(shot.shot_shape or "").strip()

            if current not in DERIVED_LABELS:
                preserved += 1
                continue

            student = students.get(shot.student_id)
            handedness = student.handedness if student else "Unknown"

            if handedness not in {"Right", "Left"}:
                unknown_hand += 1

            shot.shot_shape = classify(
                shot,
                handedness,
            )
            updated += 1

        db.commit()

        print(f"Shot shapes updated: {updated}")
        print(f"Explicit Garmin labels preserved: {preserved}")
        print(f"Shots with unknown handedness: {unknown_hand}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
