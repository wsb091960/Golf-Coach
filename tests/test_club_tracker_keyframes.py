"""Tests for keyframe club tracker using a generated video."""
import cv2
import numpy as np
from app.services.club_tracker_keyframes import track_keyframed_club


def test_tracks_visible_translating_club(tmp_path):
    path = str(tmp_path / "club.avi")
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 30, (320, 240))
    assert writer.isOpened()
    for i in range(16):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.line(frame, (80+i*2, 70), (80+i*2, 170), (255,255,255), 5)
        cv2.circle(frame, (80+i*2, 170), 9, (255,255,255), -1)
        writer.write(frame)
    writer.release()
    result = track_keyframed_club(path, [
        {"frame_index": 0, "club_grip": [80,70], "club_head": [80,170]},
        {"frame_index": 15, "club_grip": [110,70], "club_head": [110,170]},
    ])
    assert result["fps"] > 0
    assert result["frames"][0]["frame_index"] == 0
    assert result["frames"][-1]["frame_index"] == 15
    assert len(result["frames"]) > 2
    assert not result["rejected_segments"]


def test_rejects_invalid_seed(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="too short"):
        track_keyframed_club("missing.avi", [
            {"frame_index": 0, "club_grip": [1,1], "club_head": [2,2]},
            {"frame_index": 1, "club_grip": [1,1], "club_head": [10,10]},
        ])
