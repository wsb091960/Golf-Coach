"""Regression checks for validated club tracking orchestration."""
from unittest.mock import patch
from app.services.validated_club_tracking import track_validated_club


def test_rejected_image_evidence_never_becomes_accepted():
    rows = [
        {"frame_index": i, "club_grip": [i*5.0, 10.0],
         "club_head": [40.0, 70.0],
         "status": "rejected" if i == 4 else "tracked"}
        for i in range(10)
    ]
    with patch("app.services.validated_club_tracking.track_keyframed_club",
               return_value={"frames": rows, "source": "seeded_optical_flow"}), patch(
               "app.services.validated_club_tracking.validate_track_video",
               return_value={"frames": rows, "source": "seeded_optical_flow"}):
        result = track_validated_club("not-used.mp4", [], temporal_window=4)
    assert result["frames"][4]["status"] == "rejected"
    assert result["accepted_frames"] + result["rejected_frames"] == 10
    assert result["verified"] is False
    assert result["validation"] == "shaft_edge_and_temporal_motion"


def test_does_not_promote_provisional_to_verified():
    rows = [{"frame_index": 0, "club_grip": [1,1],
             "club_head": [30,30], "status": "tracked"}]
    with patch("app.services.validated_club_tracking.track_keyframed_club",
               return_value={"frames": rows}), patch(
               "app.services.validated_club_tracking.validate_track_video",
               return_value={"frames": rows}):
        result = track_validated_club("unused.mp4", [], temporal_window=8)
    assert result["accepted_frames"] == 1
    assert not result["verified"]
