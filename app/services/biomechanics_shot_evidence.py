from __future__ import annotations

from typing import Any


FIELDS = (
    "id", "shot_number", "club", "shot_shape", "source", "carry_distance",
    "total_distance", "ball_speed", "club_speed", "smash_factor",
    "launch_angle", "launch_direction", "attack_angle", "spin_rate",
    "spin_axis", "club_path", "club_face", "face_to_path",
    "offline_distance", "apex_height",
)


def _number(value: Any) -> float | None:
    if value in (None, "", "—"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def enrich_with_shot_evidence(result: dict[str, Any], shot: Any) -> dict[str, Any]:
    if not isinstance(shot, dict):
        result["shot_evidence"] = None
        result["correlations"] = []
        return result

    evidence = {key: shot.get(key) for key in FIELDS}
    correlations: list[dict[str, str]] = []
    path, face = _number(shot.get("club_path")), _number(shot.get("club_face"))
    ftp = _number(shot.get("face_to_path"))
    if ftp is None and path is not None and face is not None:
        ftp = face - path
    start, offline = _number(shot.get("launch_direction")), _number(shot.get("offline_distance"))
    attack, launch = _number(shot.get("attack_angle")), _number(shot.get("launch_angle"))
    smash = _number(shot.get("smash_factor"))

    if path is not None and face is not None:
        direction = "right" if face > 1 else "left" if face < -1 else "near target"
        curve = "right" if (ftp or 0) > 1 else "left" if (ftp or 0) < -1 else "minimal"
        correlations.append({"title": "Delivery and ball flight", "text": f"Face {face:.1f}° and path {path:.1f}° predict a start {direction} with {curve} curvature. Compare this delivery with posture and pelvic movement; video alone cannot prove the cause."})
    if start is not None or offline is not None:
        parts=[]
        if start is not None: parts.append(f"start {abs(start):.1f}° {'right' if start>0 else 'left' if start<0 else 'on line'}")
        if offline is not None: parts.append(f"finish {abs(offline):.1f} yd {'right' if offline>0 else 'left' if offline<0 else 'on line'}")
        correlations.append({"title":"Measured outcome","text":"The Garmin shot recorded "+" and ".join(parts)+". Use this outcome to prioritize the video pattern that most plausibly affects face control or strike consistency."})
    if attack is not None and launch is not None:
        correlations.append({"title":"Vertical delivery","text":f"Attack angle {attack:.1f}° produced a {launch:.1f}° launch. Evaluate setup, low-point control and dynamic loft together rather than assigning the result to one body position."})
    if smash is not None:
        quality = "efficient" if smash >= 1.42 else "moderate" if smash >= 1.30 else "low"
        correlations.append({"title":"Strike efficiency","text":f"Smash factor {smash:.2f} is {quality} for this recorded shot. Give contact quality appropriate weight before prescribing a movement change."})

    result["shot_evidence"] = evidence
    result["correlations"] = correlations
    return result
