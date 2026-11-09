"""Combine keyframe club tracking with independent evidence checks.

Only tracks passing *both* shaft-image and temporal plausibility gates are
eligible for swing synchronization. This is conservative provisional evidence,
not an automatic proof that the clubhead has been identified correctly.
"""
from __future__ import annotations
from app.services.club_tracker_keyframes import track_keyframed_club
from app.services.club_shaft_validation import validate_track_video
from app.services.club_temporal_validation import reject_stationary_head_drift


def track_validated_club(video_path, seeds, *, min_edge_fraction=0.20,
                         temporal_window=8):
    provisional = track_keyframed_club(video_path, seeds)
    image_checked = validate_track_video(
        video_path, provisional, min_edge_fraction=min_edge_fraction)
    # Temporal validator needs uninterrupted tracks; rejected image frames
    # must not bridge gaps or be interpreted as valid motion.
    rows = image_checked.get("frames", [])
    groups, current = [], []
    for row in rows:
        if (row.get("status") != "tracked" or
            (current and row["frame_index"] != current[-1]["frame_index"] + 1)):
            if current:
                groups.append(current)
            current = []
        if row.get("status") == "tracked":
            current.append(row)
    if current:
        groups.append(current)
    rejected_temporal = set()
    for group in groups:
        result = reject_stationary_head_drift(
            {"frames": group}, window=temporal_window)
        rejected_temporal.update(result["temporal_rejected_frames"])
    checked = []
    for row in rows:
        updated = dict(row)
        if updated["frame_index"] in rejected_temporal:
            updated["status"] = "rejected"
            updated["validation_reason"] = "stationary_head_with_moving_grip"
        checked.append(updated)
    accepted = sum(row.get("status") == "tracked" for row in checked)
    return {**image_checked, "frames": checked, "verified": False,
            "accepted_frames": accepted,
            "rejected_frames": len(checked) - accepted,
            "temporal_rejected_frames": sorted(rejected_temporal),
            "validation": "shaft_edge_and_temporal_motion",
            "warning": "Provisional 2D tracking; visual verification still required."}
