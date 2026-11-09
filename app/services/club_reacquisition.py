"""Conservative per-frame club shaft candidate detector.

Not a clubhead classifier. Uses image line segments near a known grip and
returns candidates requiring coach confirmation. Does not interpolate gaps.
"""
from __future__ import annotations
import cv2
import numpy as np


def shaft_candidates(frame, grip, *, min_length=35, max_grip_distance=24,
                     max_candidates=12):
    if frame is None or frame.size == 0:
        raise ValueError("Missing frame")
    g = np.asarray(grip, dtype=float)
    if g.shape != (2,) or not np.isfinite(g).all():
        raise ValueError("Invalid grip")
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 55, 135)
    lines = cv2.HoughLinesP(edges, 1, np.pi/360, threshold=28,
                            minLineLength=min_length, maxLineGap=15)
    if lines is None:
        return []
    candidates = []
    for raw in lines[:, 0]:
        a, b = raw[:2].astype(float), raw[2:].astype(float)
        v = b-a
        length = float(np.linalg.norm(v))
        if length < min_length:
            continue
        t = float(np.clip(np.dot(g-a, v)/(length*length), 0, 1))
        near = a+t*v
        distance = float(np.linalg.norm(g-near))
        if distance > max_grip_distance:
            continue
        endpoint = a if np.linalg.norm(a-g) > np.linalg.norm(b-g) else b
        score = length/(1+distance)
        candidates.append({"shaft_start": a.tolist(), "shaft_end": b.tolist(),
                           "clubhead_candidate": endpoint.tolist(),
                           "grip_distance_px": round(distance, 2),
                           "line_length_px": round(length, 2),
                           "score": round(score, 3), "verified": False})
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:max_candidates]
