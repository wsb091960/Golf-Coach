"""Metric-only coaching logic exposed through the simulator MCP tool.

This path intentionally accepts only the submitted shot metrics and optional
coach notes. It never reads or writes students, sessions, or the CRM.
"""
from __future__ import annotations

import json
import math
from typing import Any


LAWS = [
    "Centeredness of Contact",
    "Clubface Angle at Impact",
    "Clubpath at Impact",
    "Clubhead Speed at Impact",
    "Angle of Approach at Impact",
    "Dynamic Loft at Impact",
]
PRINCIPLES = [
    "Set Up", "Swing Plane", "Arc Width", "Arc Length", "Lever System",
    "Release", "Dynamic Balance", "Swing Center", "Clubhead Lag",
    "Connection", "Left Wrist Position at Impact", "Tempo", "Timing", "Rhythm",
]


def _number(metrics: dict[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _fmt(value: float | None, unit: str = "°") -> str:
    if value is None:
        return "not entered"
    return f"{value:+.1f}{unit}" if unit == "°" else f"{value:.2f}{unit}" if not unit else f"{value:.1f}{unit}"


def _curve_label(axis: float | None, handedness: str) -> str:
    if axis is None or abs(axis) <= 1:
        return "little estimated curvature"
    fades_right = (axis > 0) if handedness == "right-handed" else (axis < 0)
    return "fade / curve right" if fades_right else "draw / curve left"


def analyze_simulator_swing(
    metrics: dict[str, Any],
    handedness: str = "right-handed",
    coaching_question: str = "",
    swing_observations: str = "",
    p_positions: str = "",
    sequencing: str = "",
    mobility: str = "",
    stability: str = "",
    balance: str = "",
) -> dict[str, Any]:
    """Return an evidence-aware, metric-led coaching plan for a standalone shot."""
    hand = handedness.strip().lower()
    if hand not in {"right-handed", "left-handed"}:
        hand = "right-handed"

    face = _number(metrics, "club_face")
    path = _number(metrics, "club_path")
    entered_f2p = _number(metrics, "face_to_path")
    f2p = (face - path) if face is not None and path is not None else entered_f2p
    direction = _number(metrics, "launch_direction")
    spin_axis = _number(metrics, "spin_axis")
    axis_est = _number(metrics, "spin_axis_estimate")
    if spin_axis is None:
        spin_axis = axis_est
    if spin_axis is None and f2p is not None:
        # Same typical-driver spin-loft estimate shown in the simulator. Gear effect
        # and strike location are unknown, so label this as a rough curve estimate.
        spin_axis = math.degrees(math.atan(math.tan(math.radians(f2p)) / math.sin(math.radians(14.7))))

    ball_speed = _number(metrics, "ball_speed")
    club_speed = _number(metrics, "club_speed_estimate")
    smash = _number(metrics, "smash_factor")
    launch = _number(metrics, "launch_angle")
    spin_rate = _number(metrics, "spin_rate")
    carry = _number(metrics, "carry_distance")
    total = _number(metrics, "total_distance")
    apex = _number(metrics, "apex_height")
    axis_source = "entered" if _number(metrics, "spin_axis") is not None else "estimated"

    priorities: list[str] = []
    if path is not None and abs(path) >= 2.5:
        priorities.append("Swing Plane")
    if f2p is not None and abs(f2p) >= 1.5:
        priorities.extend(["Release", "Left Wrist Position at Impact", "Timing"])
    if face is not None and direction is not None and abs(face - direction) >= 1.5:
        priorities.extend(["Set Up", "Clubface Angle at Impact"])
    if ball_speed is not None and club_speed is not None and smash is not None and smash < 1.35:
        priorities.extend(["Centeredness of Contact", "Arc Width"])
    if balance.strip():
        priorities.append("Dynamic Balance")
    if sequencing.strip():
        priorities.extend(["Swing Center", "Connection", "Tempo", "Rhythm"])
    observation_text = f"{coaching_question} {swing_observations}".lower()
    if "chicken wing" in observation_text:
        priorities = ["Connection", "Release", "Left Wrist Position at Impact"] + priorities
    if "reverse pivot" in observation_text:
        priorities = ["Set Up", "Dynamic Balance", "Swing Center"] + priorities
    if not priorities:
        priorities = ["Set Up", "Timing", "Rhythm"]
    priorities = list(dict.fromkeys(priorities))[:5]

    goal = coaching_question.strip() or "Improve repeatability and control of the current ball flight."
    pattern = _curve_label(spin_axis, hand)
    if direction is None:
        start = "start direction not supplied"
    elif direction < -1:
        start = "starts left of target"
    elif direction > 1:
        start = "starts right of target"
    else:
        start = "starts near target"

    # Give a teaching cue based on the measured delivery relationship, while
    # leaving target selection to the coach and avoiding an assumed ideal pattern.
    if path is not None and path <= -4:
        path_coaching = "Path is notably left. First verify target line, stance, ball position, and face orientation; then rehearse a small delivery change and remeasure before progressing."
    elif path is not None and path >= 4:
        path_coaching = "Path is notably right. Verify alignment and ball position, then use a start-line station and a path gate to make the delivery less excessively rightward if the intended shot requires it."
    elif path is not None:
        path_coaching = "Path is within a modest range of the target line. Keep the path task stable and adjust face delivery only if the intended start and curve call for it."
    else:
        path_coaching = "Path was not supplied. Measure it before assigning a path-change drill."

    if f2p is not None and f2p >= 1.5:
        face_coaching = "Face is open relative to path, so a rightward curve is expected for a right-handed golfer (leftward for a left-handed golfer). Rehearse a predictable face condition; avoid forcing a hand roll without checking strike and start direction."
    elif f2p is not None and f2p <= -1.5:
        face_coaching = "Face is closed relative to path, so a leftward curve is expected for a right-handed golfer (rightward for a left-handed golfer). Rehearse a predictable face condition and confirm with measured start line and curvature."
    else:
        face_coaching = "Face and path are relatively close. Use start direction and impact location to refine the diagnosis before changing release."

    target = ""
    question_lower = goal.lower()
    if "draw" in question_lower:
        target = "For a right-handed draw, test a path modestly right of target with the face closer to target than the path; reverse the directional relationship for a left-handed golfer. Choose small increments and verify the actual start and curve."
    elif "fade" in question_lower:
        target = "For a right-handed fade, test a path modestly left of target with the face closer to target than the path; reverse the directional relationship for a left-handed golfer. Choose small increments and verify the actual start and curve."

    laws = []
    laws.append((LAWS[0], "Not measured in these inputs. Use face spray or impact tape; centeredness can change ball speed and curve through gear effect."))
    laws.append((LAWS[1], f"Face to target: {_fmt(face)}. Compare with launch direction ({_fmt(direction)}) and confirm the target line before changing face delivery."))
    laws.append((LAWS[2], f"Path: {_fmt(path)}. Face-to-path: {_fmt(f2p)} (face minus path). {path_coaching}"))
    speed_text = f"Ball speed {_fmt(ball_speed, ' mph')}; club speed {_fmt(club_speed, ' mph')}; smash {_fmt(smash, '')}." if any(x is not None for x in [ball_speed, club_speed, smash]) else "Speed metrics not supplied."
    laws.append((LAWS[3], speed_text + " Treat estimated speed or smash as a demo value until confirmed by a launch monitor."))
    laws.append((LAWS[4], "Attack angle was not supplied. Measure it before prescribing a low-point or angle-of-approach change."))
    laws.append((LAWS[5], f"Launch {_fmt(launch)}; spin rate {_fmt(spin_rate, ' rpm')}. Dynamic loft was not supplied; do not infer it from launch angle alone."))

    principle_notes = {
        "Set Up": "Verify grip, aim, stance, posture, ball position, and the target line before changing motion.",
        "Swing Plane": path_coaching,
        "Arc Width": "Support centered contact and repeatable delivery; use only if contact evidence points here.",
        "Arc Length": "A speed and distance support; not the first correction for a directional miss.",
        "Lever System": "Assess only if speed or impact delivery is also a stated goal.",
        "Release": face_coaching,
        "Dynamic Balance": "Use the balance note and video to check pressure shift and a stable finish; launch metrics alone cannot diagnose balance.",
        "Swing Center": "Coordinate body turn, arm swing, and transition only when video or sequencing notes show a mismatch.",
        "Clubhead Lag": "Do not add lag as a stand-alone fix; relate it to delivery, speed, and strike evidence.",
        "Connection": "Use if video shows the arms and torso losing useful coordination; do not force a fixed connection.",
        "Left Wrist Position at Impact": face_coaching + (" For a left-handed golfer, this refers to the lead wrist, which is the right wrist." if hand == "left-handed" else ""),
        "Tempo": "Keep the pace repeatable while changing one delivery variable at a time.",
        "Timing": "Retest face and path together; their relationship influences curvature.",
        "Rhythm": "Use a repeatable sequence and finish, then compare a new block of measured shots.",
    }

    lines = [
        "Ball Flight Coaching Analysis",
        "",
        "1. Ball-Flight Read",
        f"Goal: {goal}",
        f"Golfer: {hand}",
        f"Pattern estimate: {start}; {pattern}.",
        f"Face {_fmt(face)} · Path {_fmt(path)} · Face-to-path {_fmt(f2p)} · Spin axis {_fmt(spin_axis)} ({axis_source}).",
        f"Ball speed {_fmt(ball_speed, ' mph')} · Club speed {_fmt(club_speed, ' mph')} · Smash {_fmt(smash, '')} · Launch {_fmt(launch)} · Spin {_fmt(spin_rate, ' rpm')}.",
        f"Carry {_fmt(carry, ' yd')} · Total {_fmt(total, ' yd')} · Apex {_fmt(apex, ' ft')}.",
        "The spin-axis value is an estimate unless entered as a measured value. Strike location, attack angle, and dynamic loft are not provided.",
        "",
        "2. The Six Laws — What the Metrics Show",
    ]
    lines.extend(f"{i}. {name}: {description}" for i, (name, description) in enumerate(laws, start=1))
    lines.extend(["", "3. Coaching Priority"])
    lines.extend(f"- {name}: {principle_notes[name]}" for name in priorities)
    lines.extend(["", "4. Coaching Plan", "Setup check:"])
    lines.append("- Recheck aim, stance, ball position, grip, and face orientation against the intended target. Change setup only after confirming the current alignment.")
    if "chicken wing" in observation_text:
        lines.append("- For a reported chicken wing, inspect P9–P10 on video and check whether the lead-arm fold is a response to face/path delivery, contact, or body motion. Screen shoulder/thoracic mobility and trunk stability before prescribing a held-off or connected finish.")
    if "reverse pivot" in observation_text:
        lines.append("- For a reported reverse pivot, review setup and pressure movement at P2–P3 and through transition; use a balance screen before adding a forceful weight-shift cue.")
    lines.append("Transition / delivery:")
    lines.append(f"- {path_coaching}")
    lines.append(f"- Face control: {face_coaching}")
    lines.append("Practice station:")
    if path is not None and path <= -4:
        lines.append("- Use a short rehearsal at reduced speed to explore a small delivery change. Recheck face and path before increasing speed.")
    elif path is not None and abs(path) >= 2.5:
        lines.append("- Set a clear start-line task and, if useful, a visual path constraint. Begin with a small change from the measured delivery and adjust the task as the pattern changes.")
    else:
        lines.append("- Use a start-line station with face spray; hold the path task steady while testing small face-delivery changes.")
    lines.append("- Hit 3 rehearsal swings, then 5 balls at partial speed. Record face, path, start direction, spin axis, and strike before increasing speed.")
    lines.append("Success check:")
    lines.append("- Pass when at least 4 of 5 shots show the intended start/curve window and centered contact without losing balance. Repeat for a second set before keeping the change.")
    if target:
        lines.append(f"- Intended-shape reference: {target}")
    lines.extend(["", "5. The Fourteen Principles — Coaching Map"])
    for i, name in enumerate(PRINCIPLES, start=1):
        status = "Primary focus" if name in priorities else "Supporting check"
        lines.append(f"{i}. {name} — {status}. {principle_notes[name]}")
    lines.extend(["", "6. TGM, TPI, and P-Position Cross-Check"])
    lines.append("- TGM: Keep the three imperatives in view—clubpath control, clubface alignment, and timing. Preserve balance and rhythm; this metric-only screen cannot confirm impact alignments or motion details.")
    lines.append("- TPI: No physical screen was supplied. Use the mobility, stability, and balance notes below to decide whether the player can access the proposed motion; do not force a position that the body cannot produce.")
    lines.append("- P-Positions: Launch metrics do not identify P1–P10. Use the coach's observations to select the relevant checkpoints and confirm them on video.")
    for label, note in [("P-position notes", p_positions), ("Sequencing notes", sequencing), ("Mobility notes", mobility), ("Stability notes", stability), ("Balance notes", balance), ("Swing observations", swing_observations)]:
        if note.strip():
            lines.append(f"- {label}: {note.strip()}")
    lines.extend(["", "Coaching Caution", "Treat example numbers and feels as starting references, not universal prescriptions. Individualize for club, strike, skill, handedness, mobility, and measured ball flight. Change one variable at a time."])

    return {"analysis": "\n".join(lines), "primary_principles": priorities, "pattern": pattern, "face_to_path": f2p, "spin_axis": spin_axis, "spin_axis_source": axis_source}


def analyze_simulator_swing_json(**kwargs: Any) -> str:
    """MCP wrapper-friendly deterministic JSON response."""
    metrics = kwargs.pop("metrics", {})
    return json.dumps(analyze_simulator_swing(metrics if isinstance(metrics, dict) else {}, **kwargs), ensure_ascii=False)
