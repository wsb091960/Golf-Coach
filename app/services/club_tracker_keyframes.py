"""Keyframe-assisted club tracking for high-speed golf video.

Seed grip/head at several coach-verified frames. Track each segment with LK
optical flow; when tracking fails, leave a gap rather than invent a location.
Segments are anchored to their *ending* keyframe to reject drift.
"""
from __future__ import annotations
from math import hypot
from typing import Any
import cv2
import numpy as np


def _points(seed):
    pts = np.asarray([seed["club_grip"], seed["club_head"]], dtype=np.float32)
    if pts.shape != (2, 2) or not np.isfinite(pts).all():
        raise ValueError("Seed requires finite grip and head coordinates")
    if np.linalg.norm(pts[0]-pts[1]) < 8:
        raise ValueError("Seed shaft is too short")
    return pts.reshape(2, 1, 2)


def _lk(prev, curr, points, max_fb_error, max_step):
    options = dict(winSize=(41,41), maxLevel=4,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, .01))
    nxt, status, _ = cv2.calcOpticalFlowPyrLK(prev, curr, points, None, **options)
    if nxt is None or status is None or not np.all(status):
        return None
    back, back_status, _ = cv2.calcOpticalFlowPyrLK(curr, prev, nxt, None, **options)
    if back is None or back_status is None or not np.all(back_status):
        return None
    error = np.linalg.norm(back.reshape(2,2)-points.reshape(2,2), axis=1)
    step = np.linalg.norm(nxt.reshape(2,2)-points.reshape(2,2), axis=1)
    if np.any(error > max_fb_error) or np.any(step > max_step):
        return None
    return nxt


def track_keyframed_club(video_path: str, seeds: list[dict[str, Any]],
                         *, max_fb_error: float = 3.0,
                         max_step_px: float = 95.0,
                         anchor_tolerance_px: float = 30.0) -> dict:
    """Return only validated per-frame club coordinates.

    Keyframes contain frame_index, club_grip, club_head. No automatic seed
    discovery is claimed. Rejected segments are omitted and reported.
    """
    if len(seeds) < 2:
        raise ValueError("At least two verified club keyframes are required")
    seeds = sorted(seeds, key=lambda s: s["frame_index"])
    ids = [s["frame_index"] for s in seeds]
    if any(not isinstance(i, int) or i < 0 for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Keyframe indices must be unique nonnegative integers")
    anchors = {s["frame_index"]: _points(s) for s in seeds}
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        cap.release()
        raise ValueError("Invalid FPS")
    output = {}
    rejected = []
    try:
        for start, end in zip(ids[:-1], ids[1:]):
            cap.set(cv2.CAP_PROP_POS_FRAMES, start)
            ok, frame = cap.read()
            if not ok:
                rejected.append({"start": start, "end": end, "reason": "unreadable start"})
                continue
            prev = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            points = anchors[start].copy()
            segment = {start: points.copy()}
            for idx in range(start+1, end+1):
                ok, frame = cap.read()
                if not ok:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                nxt = _lk(prev, gray, points, max_fb_error, max_step_px)
                if nxt is None:
                    break
                segment[idx] = nxt.copy()
                prev, points = gray, nxt
            if end not in segment:
                rejected.append({"start": start, "end": end, "reason": "tracking lost"})
                output[start] = anchors[start]
                output[end] = anchors[end]
                continue
            error = np.linalg.norm(segment[end].reshape(2,2)-anchors[end].reshape(2,2), axis=1)
            if np.any(error > anchor_tolerance_px):
                rejected.append({"start": start, "end": end, "reason": "endpoint drift",
                                 "endpoint_error_px": [round(float(v),2) for v in error]})
                output[start] = anchors[start]
                output[end] = anchors[end]
                continue
            output.update(segment)
            output[end] = anchors[end]
    finally:
        cap.release()
    frames = []
    for idx, pts in sorted(output.items()):
        grip, head = pts.reshape(2,2).tolist()
        frames.append({"frame_index": idx, "time": idx/fps, "club_grip": grip,
                       "club_head": head, "status": "tracked",
                       "provenance": "coach_keyframe" if idx in anchors else "optical_flow"})
    return {"fps": fps, "source": "seeded_optical_flow", "frames": frames,
            "rejected_segments": rejected, "verified": False,
            "warning": "2D provisional tracking. Review overlay and confirm all keyframes."}
