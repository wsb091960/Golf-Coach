from pathlib import Path

path = Path("app/routers/importer.py")
text = path.read_text(encoding="utf-8")

start = text.find("def derive_shot_shape(")
end_marker = "\n# ==========================================================\n# PRIMARY CLUB"
end = text.find(end_marker, start)

if start == -1 or end == -1:
    raise SystemExit(
        "Could not find derive_shot_shape() / PRIMARY CLUB section. "
        "Install Phase 2.1.2 first."
    )

replacement = '''def derive_shot_shape(
    shot: dict[str, Any],
    handedness: str = "Unknown",
) -> str:
    explicit = str(shot.get("shot_shape") or "").strip()

    if explicit:
        return explicit

    face_to_path = shot.get("face_to_path")

    if (
        face_to_path is None
        and shot.get("club_face") is not None
        and shot.get("club_path") is not None
    ):
        face_to_path = (
            float(shot["club_face"])
            - float(shot["club_path"])
        )

    curve_direction = "Straight"
    curve_amount = 0.0

    if face_to_path is not None:
        curve_amount = float(face_to_path)

        if abs(curve_amount) <= 1.0:
            curve_direction = "Straight"
        elif curve_amount < 0:
            curve_direction = "Left"
        else:
            curve_direction = "Right"

    elif shot.get("spin_axis") is not None:
        curve_amount = float(shot["spin_axis"])

        if abs(curve_amount) <= 2.0:
            curve_direction = "Straight"
        elif curve_amount < 0:
            curve_direction = "Left"
        else:
            curve_direction = "Right"

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
'''

text = text[:start] + replacement + text[end:]

old = '''shot[
            "shot_shape"
        ] = derive_shot_shape(
            shot
        )'''

new = '''student = get_student(
            str(session.get("student_id", "")),
            db=db,
        )

        handedness = (
            student.get("handedness", "Unknown")
            if student
            else "Unknown"
        )

        shot[
            "shot_shape"
        ] = derive_shot_shape(
            shot,
            handedness,
        )'''

if old not in text:
    compact_old = 'shot["shot_shape"] = derive_shot_shape(shot)'
    compact_new = '''student = get_student(
            str(session.get("student_id", "")),
            db=db,
        )
        handedness = (
            student.get("handedness", "Unknown")
            if student
            else "Unknown"
        )
        shot["shot_shape"] = derive_shot_shape(
            shot,
            handedness,
        )'''
    if compact_old not in text:
        raise SystemExit("Could not find shot-shape call site in importer.py.")
    text = text.replace(compact_old, compact_new, 1)
else:
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Updated app/routers/importer.py for handedness-aware shot shape")
