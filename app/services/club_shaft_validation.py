"""Independent image-evidence check for provisional golf-club tracks.

Rejects tracks without a visible line-like shaft between grip and clubhead.
This is a conservative 2D quality gate, not a trained club detector.
"""
from __future__ import annotations

import cv2
import numpy as np


def validate_shaft_frame(image, grip, head, *, min_length=18.0,
                         min_edge_fraction=0.20, max_offset_px=5):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    g, h = np.asarray(grip, dtype=float), np.asarray(head, dtype=float)
    length = float(np.linalg.norm(h-g))
    if not np.isfinite(length) or length < min_length:
        return {"accepted": False, "reason": "invalid_or_short_shaft", "edge_fraction": 0.0}
    height, width = gray.shape[:2]
    if any(p[0] < 0 or p[0] >= width or p[1] < 0 or p[1] >= height for p in (g,h)):
        return {"accepted": False, "reason": "outside_frame", "edge_fraction": 0.0}
    edges = cv2.Canny(gray, 60, 150)
    count = max(20, int(length))
    fractions = []
    direction = (h-g)/length
    normal = np.array([-direction[1], direction[0]])
    # Ignore endpoints, where hands and clubhead can produce unrelated edges.
    for offset in np.linspace(-max_offset_px, max_offset_px, 5):
        hits = 0
        samples = 0
        for t in np.linspace(.15, .85, count):
            x, y = g + t*(h-g) + offset*normal
            xi, yi = int(round(x)), int(round(y))
            if 0 <= xi < width and 0 <= yi < height:
                samples += 1
                hits += bool(edges[yi,xi])
        fractions.append(hits/max(samples,1))
    fraction = max(fractions, default=0.0)
    return {"accepted": fraction >= min_edge_fraction,
            "reason": "shaft_edge_supported" if fraction >= min_edge_fraction else "no_shaft_edge_support",
            "edge_fraction": round(float(fraction), 3)}


def validate_track_video(video_path, track, *, min_edge_fraction=.20):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Video could not be opened")
    checked = []
    try:
        for row in track.get("frames", []):
            idx = row["frame_index"]
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, image = cap.read()
            if not ok:
                checked.append({**row, "status": "rejected", "validation_reason": "frame_unreadable"})
                continue
            result = validate_shaft_frame(image, row["club_grip"], row["club_head"],
                                          min_edge_fraction=min_edge_fraction)
            checked.append({**row, "status": "tracked" if result["accepted"] and row.get("status") == "tracked" else "rejected",
                            "validation_reason": result["reason"],
                            "shaft_edge_fraction": result["edge_fraction"]})
    finally:
        cap.release()
    return {**track, "frames": checked, "verified": False,
            "validation": "independent_2d_shaft_edge_gate",
            "warning": "Edge evidence is necessary but not sufficient; coach must verify overlay."}
