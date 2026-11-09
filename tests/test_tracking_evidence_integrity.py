"""Regression tests for rejected evidence never becoming valid tracking."""
from unittest.mock import patch
import numpy as np
from app.services.club_shaft_validation import validate_track_video
from app.services.swing_track_sync import synchronize_tracks


def test_shaft_gate_never_promotes_previously_rejected_track():
    class FakeCap:
        def isOpened(self): return True
        def set(self, *_): return True
        def read(self): return True, np.zeros((120, 120, 3), dtype=np.uint8)
        def release(self): pass
    original = {"frames": [{"frame_index": 0, "status": "rejected",
                            "club_grip": [20, 20], "club_head": [80, 80]}]}
    with patch("app.services.club_shaft_validation.cv2.VideoCapture", return_value=FakeCap()), patch(
         "app.services.club_shaft_validation.validate_shaft_frame",
         return_value={"accepted": True, "reason": "shaft_edge_supported", "edge_fraction": 0.8}):
        result = validate_track_video("unused.mp4", original)
    assert result["frames"][0]["status"] == "rejected"


def test_club_coordinates_do_not_count_as_body_pose():
    pose = {"fps": 30, "width": 100, "height": 100,
            "frames": [{"frame_index": 0, "pose_detected": True, "landmarks": {}}]}
    club = {"fps": 30, "source": "seeded_optical_flow",
            "frames": [{"frame_index": 0, "status": "tracked",
                        "club_grip": [20,20], "club_head": [80,80]}]}
    result = synchronize_tracks(pose, club)
    assert result["frames"][0]["pose_status"] == "missing"
    assert result["frames"][0]["club_status"] == "provisional"
