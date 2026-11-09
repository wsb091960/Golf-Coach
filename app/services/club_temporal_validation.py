"""Temporal plausibility gate for provisional clubhead tracks.

A clubhead that stays nearly stationary while the grip moves substantially
indicates optical-flow lock-on to background, not a reliable club track.
This conservative rule is not proof of correct tracking when it passes.
"""
from math import hypot


def reject_stationary_head_drift(track, *, window=8, grip_motion_px=25,
                                 head_motion_px=5):
    if window < 2:
        raise ValueError("window must be at least 2")
    rows = [dict(row) for row in track.get("frames", [])]
    rejected = set()
    for start in range(0, len(rows)-window+1):
        group = rows[start:start+window]
        indices = [r["frame_index"] for r in group]
        if indices[-1]-indices[0] != window-1:
            continue
        def travel(key):
            a, b = group[0][key], group[-1][key]
            return hypot(b[0]-a[0], b[1]-a[1])
        if travel("club_grip") >= grip_motion_px and travel("club_head") <= head_motion_px:
            rejected.update(indices)
    for row in rows:
        if row["frame_index"] in rejected:
            row["status"] = "rejected"
            row["validation_reason"] = "stationary_head_with_moving_grip"
    return {**track, "frames": rows, "verified": False,
            "temporal_rejected_frames": sorted(rejected)}
