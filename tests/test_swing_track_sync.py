"""Regression tests for synchronizing tracked golf swing evidence."""
import pytest
from app.services.swing_track_sync import synchronize_tracks


def tracks():
    pose = {"fps": 60.0, "width": 640, "height": 480, "frames": [
        {"frame_index": 0, "pose_detected": True,
         "landmarks": {"left_shoulder": [110, 120], "left_wrist": [100, 200],
                       "right_elbow": [140, 180]}},
        {"frame_index": 2, "pose_detected": False, "landmarks": {}},
    ]}
    club = {"fps": 60.0, "source": "seeded_optical_flow", "frames": [
        {"frame_index": 0, "club_grip": [100, 200], "club_head": [180, 200], "status": "tracked"},
        {"frame_index": 1, "club_grip": [100, 200], "club_head": [101, 200], "status": "tracked"},
    ]}
    return pose, club


def test_merge_preserves_original_frame_indices_and_missing_values():
    merged = synchronize_tracks(*tracks())
    assert [f["frame_index"] for f in merged["frames"]] == [0, 1, 2]
    assert merged["frames"][0]["lead_shoulder"] == [110, 120]
    assert merged["frames"][0]["shaft_angle_deg"] == 0
    assert merged["frames"][1]["club_status"] == "rejected"
    assert "club_head" not in merged["frames"][1]
    assert merged["frames"][2]["club_status"] == "missing"
    assert merged["club_frames_accepted"] == 1


def test_rejects_fps_mismatch():
    pose, club = tracks()
    club["fps"] = 120
    with pytest.raises(ValueError, match="FPS mismatch"):
        synchronize_tracks(pose, club)


def test_rejects_duplicate_indices():
    pose, club = tracks()
    club["frames"].append(dict(club["frames"][0]))
    with pytest.raises(ValueError, match="unique"):
        synchronize_tracks(pose, club)


def test_left_handed_lead_side():
    pose, club = tracks()
    pose["frames"][0]["landmarks"]["right_shoulder"] = [150, 120]
    assert synchronize_tracks(pose, club, handedness="left")["frames"][0]["lead_shoulder"] == [150, 120]


def test_rejects_invalid_coordinates():
    pose, club = tracks()
    club["frames"][0]["club_head"] = [float("nan"), 20]
    result = synchronize_tracks(pose, club)
    assert result["frames"][0]["club_status"] == "rejected"
