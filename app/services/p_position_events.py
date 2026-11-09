"""Detect P1-P10 events from tracked, timestamped swing landmarks.

This module consumes *automatically tracked* points; it does not pretend that
landmarks can be obtained from raw video without a pose/club tracking model.
Each frame: time, wrist, lead_shoulder, trail_elbow, club_head, club_grip,
and optional ball. Coordinates are image pixels (y increases downward).
"""
from __future__ import annotations

from math import atan2, degrees, hypot
from typing import Any

PHASES = ("p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10")


def _xy(frame: dict[str, Any], key: str) -> tuple[float, float]:
    value = frame[key]
    if len(value) != 2:
        raise ValueError(f"{key} must have two coordinates")
    return float(value[0]), float(value[1])


def _horizontal(frame: dict[str, Any], a: str, b: str, tolerance: float = 15) -> bool:
    ax, ay = _xy(frame, a)
    bx, by = _xy(frame, b)
    angle = abs(degrees(atan2(by - ay, bx - ax)))
    return min(angle, abs(180 - angle)) <= tolerance


def _arm_parallel(frame: dict[str, Any], tolerance: float = 15) -> bool:
    return _horizontal(frame, "lead_shoulder", "wrist", tolerance)


def _shaft_parallel(frame: dict[str, Any], tolerance: float = 15) -> bool:
    return _horizontal(frame, "club_grip", "club_head", tolerance)


def _club_height(frame: dict[str, Any]) -> float:
    return _xy(frame, "club_head")[1]


def _impact_distance(frame: dict[str, Any]) -> float:
    hx, hy = _xy(frame, "club_head")
    bx, by = _xy(frame, "ball")
    return hypot(hx - bx, hy - by)


def _closest(frames: list[dict[str, Any]], indices: range, predicate, label: str) -> int:
    candidates = [i for i in indices if predicate(frames[i])]
    if not candidates:
        raise ValueError(f"Cannot reliably detect {label}; missing event or obscured club")
    return candidates[0]


def detect_positions(frames: list[dict[str, Any]], *, address_index: int,
                     impact_index: int, finish_index: int) -> dict[str, dict[str, Any]]:
    """Detect events with monotonic phase order; fail rather than fabricate frames.

    Address, impact and finish anchors must be independently detected or
    coach-verified. This function never infers 3D joint rotation from 2D video.
    """
    if not (0 <= address_index < impact_index < finish_index < len(frames)):
        raise ValueError("Address, impact and finish anchors must be in time order")
    top = min(range(address_index + 1, impact_index), key=lambda i: _club_height(frames[i]))
    if top <= address_index + 2 or top >= impact_index - 2:
        raise ValueError("Top of backswing cannot be established")
    p2 = _closest(frames, range(address_index + 1, top), _shaft_parallel, "P2")
    p3 = _closest(frames, range(p2 + 1, top), _arm_parallel, "P3")
    p5 = _closest(frames, range(top + 1, impact_index), _arm_parallel, "P5")
    p6 = _closest(frames, range(p5 + 1, impact_index), _shaft_parallel, "P6")
    p8 = _closest(frames, range(impact_index + 1, finish_index), _shaft_parallel, "P8")
    p9 = _closest(frames, range(p8 + 1, finish_index), lambda f: _horizontal(f, "trail_elbow", "wrist"), "P9")
    indices = (address_index, p2, p3, top, p5, p6, impact_index, p8, p9, finish_index)
    if list(indices) != sorted(set(indices)):
        raise ValueError("Detected P-positions overlap or are out of order")
    return {phase: {"frame_index": idx, "time": float(frames[idx]["time"]),
                    "source": "tracked-landmarks", "verified": False}
            for phase, idx in zip(PHASES, indices)}
