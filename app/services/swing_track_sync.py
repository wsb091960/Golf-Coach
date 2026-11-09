"""Synchronize pose and club tracks using original video frame indices.

No invented landmarks: missing or rejected club points remain absent.
The output can be consumed by P-position event detection after anchor validation.
"""
from __future__ import annotations

from math import atan2, degrees, hypot, isfinite
from typing import Any


def _point(value: Any) -> list[float] | None:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        return None
    try:
        x, y = float(value[0]), float(value[1])
    except (ValueError, TypeError):
        return None
    return [x, y] if isfinite(x) and isfinite(y) else None


def synchronize_tracks(pose: dict[str, Any], club: dict[str, Any],
                       *, handedness: str = "right",
                       fps_tolerance: float = 0.02) -> dict[str, Any]:
    """Merge on frame_index, never rounded timestamps or array positions.

    Pose and club coordinates must refer to the same original video pixels.
    Supports partial coverage; outputs explicit missing-data statuses.
    """
    if handedness not in ("right", "left"):
        raise ValueError("handedness must be right or left")
    pose_fps, club_fps = float(pose["fps"]), float(club["fps"])
    if not isfinite(pose_fps) or not isfinite(club_fps) or min(pose_fps, club_fps) <= 0:
        raise ValueError("FPS must be finite and positive")
    if abs(pose_fps - club_fps) / max(pose_fps, club_fps) > fps_tolerance:
        raise ValueError("Track FPS mismatch; cannot synchronize safely")
    if club.get("source") not in ("seeded_optical_flow", "verified_club_tracker"):
        raise ValueError("Club track source is unknown")
    pose_rows = pose.get("frames", [])
    club_rows = club.get("frames", [])
    def index_rows(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
        out = {}
        for row in rows:
            idx = row.get("frame_index")
            if not isinstance(idx, int) or idx < 0 or idx in out:
                raise ValueError("Frame indices must be unique nonnegative integers")
            out[idx] = row
        return out
    pose_by_frame, club_by_frame = index_rows(pose_rows), index_rows(club_rows)
    width, height = int(pose["width"]), int(pose["height"])
    if width <= 0 or height <= 0:
        raise ValueError("Invalid video dimensions")
    results = []
    accepted = 0
    for idx in sorted(pose_by_frame.keys() | club_by_frame.keys()):
        pr, cr = pose_by_frame.get(idx), club_by_frame.get(idx)
        points = {}
        if pr:
            for name, value in (pr.get("landmarks") or {}).items():
                xy = _point(value)
                if xy is not None and 0 <= xy[0] < width and 0 <= xy[1] < height:
                    points[name] = xy
        club_status = "missing"
        if cr:
            grip, head = _point(cr.get("club_grip")), _point(cr.get("club_head"))
            if (cr.get("status") == "tracked" and grip and head and
                all(0 <= p[0] < width and 0 <= p[1] < height for p in (grip, head)) and
                hypot(head[0]-grip[0], head[1]-grip[1]) >= 8):
                points["club_grip"], points["club_head"] = grip, head
                club_status = "provisional"
                accepted += 1
            else:
                club_status = "rejected"
        lead = "left" if handedness == "right" else "right"
        trail = "right" if handedness == "right" else "left"
        for dest, name in (("lead_shoulder", f"{lead}_shoulder"),
                           ("trail_elbow", f"{trail}_elbow"),
                           ("wrist", f"{lead}_wrist")):
            if name in points:
                points[dest] = points[name]
        result = {"frame_index": idx, "time": round(idx / pose_fps, 6),
                  "pose_status": "tracked" if pr and pr.get("pose_detected") and (pr.get("landmarks") or {}) else "missing",
                  "club_status": club_status, **points}
        if club_status == "provisional":
            g, h = points["club_grip"], points["club_head"]
            result["shaft_angle_deg"] = round(degrees(atan2(h[1]-g[1], h[0]-g[0])), 2)
        results.append(result)
    return {"fps": pose_fps, "width": width, "height": height, "handedness": handedness,
            "frames": results, "club_frames_accepted": accepted,
            "club_frames_rejected": sum(f["club_status"] == "rejected" for f in results),
            "verified": False,
            "warning": "Provisional 2D evidence. Coach validation required before P-position measurements."}
