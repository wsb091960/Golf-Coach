from __future__ import annotations

from dataclasses import asdict, dataclass
from math import atan2, degrees, hypot
from typing import Any


Point = tuple[float, float]


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    value: float
    unit: str
    confidence: int
    status: str
    coaching_note: str


def _point(raw: Any) -> Point:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError("Each landmark must contain x and y coordinates.")
    return float(raw[0]), float(raw[1])


def _line_angle(a: Point, b: Point) -> float:
    return degrees(atan2(b[1] - a[1], b[0] - a[0]))


def _distance(a: Point, b: Point) -> float:
    return hypot(b[0] - a[0], b[1] - a[1])


def _midpoint(a: Point, b: Point) -> Point:
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _tilt_from_horizontal(a: Point, b: Point) -> float:
    angle = _line_angle(a, b)
    while angle > 90:
        angle -= 180
    while angle < -90:
        angle += 180
    return round(angle, 1)


def _status(value: float, low: float, high: float) -> str:
    if low <= value <= high:
        return "on-track"
    return "watch" if low * 0.75 <= value <= high * 1.25 else "priority"


def analyze_landmarks(payload: dict[str, Any]) -> dict[str, Any]:
    """Analyze coach-verified 2D landmarks from key swing frames.

    Coordinates are normalized to the video canvas. This intentionally reports
    screen-plane estimates—not laboratory 3D kinetics.
    """
    frames = payload.get("frames") or {}
    if not frames:
        raise ValueError("At least one key frame is required.")

    camera_view = str(payload.get("camera_view") or "down-the-line")
    handedness = str(payload.get("handedness") or "right")
    metrics: list[Metric] = []

    address = frames.get("address") or {}
    top = frames.get("top") or {}
    impact = frames.get("impact") or {}
    finish = frames.get("finish") or {}

    def points(frame: dict[str, Any], *names: str) -> list[Point] | None:
        try:
            return [_point(frame[name]) for name in names]
        except (KeyError, TypeError, ValueError):
            return None

    address_torso = points(address, "left_shoulder", "right_shoulder", "left_hip", "right_hip")
    top_torso = points(top, "left_shoulder", "right_shoulder", "left_hip", "right_hip")
    impact_torso = points(impact, "left_shoulder", "right_shoulder", "left_hip", "right_hip")

    if address_torso:
        ls, rs, lh, rh = address_torso
        shoulder_mid, hip_mid = _midpoint(ls, rs), _midpoint(lh, rh)
        spine = abs(90 - abs(_line_angle(hip_mid, shoulder_mid)))
        metrics.append(Metric("address_spine", "Address spine tilt", round(spine, 1), "°", 86,
                              _status(spine, 4, 18), "Use as the posture baseline for change through impact."))

    if top_torso:
        ls, rs, lh, rh = top_torso
        shoulder_tilt = abs(_tilt_from_horizontal(ls, rs))
        hip_tilt = abs(_tilt_from_horizontal(lh, rh))
        metrics.extend([
            Metric("top_shoulder_tilt", "Top shoulder tilt", shoulder_tilt, "°", 82,
                   _status(shoulder_tilt, 25, 48), "Match tilt to turn without collapsing toward the ball."),
            Metric("top_hip_tilt", "Top hip tilt", hip_tilt, "°", 78,
                   _status(hip_tilt, 8, 25), "Preserve trail-hip depth while the pelvis turns."),
        ])

    if address_torso and impact_torso:
        als, ars, alh, arh = address_torso
        ils, irs, ilh, irh = impact_torso
        address_hip_mid = _midpoint(alh, arh)
        impact_hip_mid = _midpoint(ilh, irh)
        stance = max(_distance(alh, arh), 0.001)
        pelvic_shift = (impact_hip_mid[0] - address_hip_mid[0]) / stance * 100
        if handedness == "left":
            pelvic_shift *= -1
        metrics.append(Metric("pelvic_shift", "Pelvic shift at impact", round(pelvic_shift, 1), "% stance", 79,
                              _status(pelvic_shift, 8, 38), "Confirm pressure moves forward without a pelvis slide."))

        address_shoulder_mid = _midpoint(als, ars)
        impact_shoulder_mid = _midpoint(ils, irs)
        address_posture = abs(90 - abs(_line_angle(address_hip_mid, address_shoulder_mid)))
        impact_posture = abs(90 - abs(_line_angle(impact_hip_mid, impact_shoulder_mid)))
        posture_change = impact_posture - address_posture
        metrics.append(Metric("posture_change", "Posture change to impact", round(posture_change, 1), "°", 84,
                              _status(abs(posture_change), 0, 8), "A large loss supports an early-extension finding."))

    if finish:
        if camera_view == "face-on":
            face_on_finish = points(finish, "nose", "left_shoulder", "right_shoulder", "left_ankle", "right_ankle")
            if face_on_finish:
                nose, ls, rs, la, ra = face_on_finish
                shoulder_width = max(_distance(ls, rs), 0.001)
                lead_ankle = la if handedness == "right" else ra
                offset = abs(nose[0] - lead_ankle[0]) / shoulder_width * 100
                metrics.append(Metric("finish_head_support", "Finish head-to-lead-foot offset", round(offset, 1), "% shoulder width", 72,
                                      _status(offset, 0, 65), "Face-on estimate of head position relative to lead-side support; confirm the player can hold the finish."))
        else:
            dtl_finish = points(finish, "left_shoulder", "right_shoulder", "left_hip", "right_hip")
            if dtl_finish:
                ls, rs, lh, rh = dtl_finish
                shoulder_mid = _midpoint(ls, rs)
                hip_mid = _midpoint(lh, rh)
                shoulder_width = max(_distance(ls, rs), 0.001)
                offset = abs(shoulder_mid[0] - hip_mid[0]) / shoulder_width * 100
                metrics.append(Metric("finish_torso_stack", "Finish torso-to-pelvis stack", round(offset, 1), "% shoulder width", 75,
                                      _status(offset, 0, 35), "Down-the-line estimate of upper-body stacking over the pelvis; confirm lead-side support and no recovery step."))

    confidence = round(sum(m.confidence for m in metrics) / len(metrics)) if metrics else 0
    priorities = [asdict(m) for m in metrics if m.status == "priority"]
    watches = [asdict(m) for m in metrics if m.status == "watch"]

    return {
        "camera_view": camera_view,
        "handedness": handedness,
        "confidence": confidence,
        "metrics": [asdict(metric) for metric in metrics],
        "priorities": priorities[:3],
        "watches": watches[:3],
        "disclaimer": "2D screen-plane estimates from coach-verified landmarks; not a medical assessment or 3D force/kinetics measurement.",
    }

