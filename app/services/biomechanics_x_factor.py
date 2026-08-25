from __future__ import annotations

from math import acos, degrees, hypot
from typing import Any


def _point(frame: dict[str, Any], name: str) -> tuple[float, float] | None:
    value = frame.get(name)
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        return float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None


def _width(frame: dict[str, Any], left: str, right: str) -> float | None:
    a, b = _point(frame, left), _point(frame, right)
    if not a or not b:
        return None
    return hypot(b[0] - a[0], b[1] - a[1])


def _turn(current: float, baseline: float) -> tuple[float, bool]:
    ratio = current / max(baseline, 0.0001)
    suspect = ratio > 1.10 or ratio < 0.18
    ratio = min(1.0, max(0.0, ratio))
    return degrees(acos(ratio)), suspect


def enrich_with_x_factor(result: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    view = str(payload.get("camera_view") or "down-the-line").lower()
    if view != "face-on":
        result["x_factor"] = {"available": False, "reason": "A defensible 2D X-factor estimate requires a properly aligned face-on video."}
        return result

    visual = payload.get("visual_frames") or {}
    p1, p4, p5 = visual.get("p1") or {}, visual.get("p4") or {}, visual.get("p5") or {}
    if not all((p1, p4, p5)):
        result["x_factor"] = {"available": False, "reason": "Complete P1, P4 and P5 to estimate rotational separation."}
        return result

    values = {
        "s1": _width(p1, "left_shoulder", "right_shoulder"),
        "h1": _width(p1, "left_hip", "right_hip"),
        "s4": _width(p4, "left_shoulder", "right_shoulder"),
        "h4": _width(p4, "left_hip", "right_hip"),
        "s5": _width(p5, "left_shoulder", "right_shoulder"),
        "h5": _width(p5, "left_hip", "right_hip"),
    }
    if any(value is None or value <= 0 for value in values.values()):
        result["x_factor"] = {"available": False, "reason": "Shoulder and hip landmarks are incomplete or too close together for a stable estimate."}
        return result

    thorax4, q1 = _turn(values["s4"], values["s1"])
    pelvis4, q2 = _turn(values["h4"], values["h1"])
    thorax5, q3 = _turn(values["s5"], values["s1"])
    pelvis5, q4 = _turn(values["h5"], values["h1"])
    x4 = abs(thorax4 - pelvis4)
    x5 = abs(thorax5 - pelvis5)
    stretch = x5 - x4
    confidence = 58 if any((q1, q2, q3, q4)) else 68

    result["x_factor"] = {
        "available": True,
        "confidence": confidence,
        "method": "2D face-on apparent-width estimate",
        "p4_thorax_turn": round(thorax4, 1),
        "p4_pelvis_turn": round(pelvis4, 1),
        "p4_x_factor": round(x4, 1),
        "p5_thorax_turn": round(thorax5, 1),
        "p5_pelvis_turn": round(pelvis5, 1),
        "p5_separation": round(x5, 1),
        "x_factor_stretch": round(stretch, 1),
        "quality_warning": "One or more apparent widths were outside the preferred range; verify landmark placement." if any((q1, q2, q3, q4)) else "",
        "coaching_note": "Use as a within-player comparison. Do not chase a tour benchmark or interpret separation as power by itself.",
    }
    return result
