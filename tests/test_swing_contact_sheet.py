"""Regression tests for decoded-frame contact-sheet extraction."""
import json

import cv2
import numpy as np
import pytest
from PIL import Image

from scripts.extract_swing_contact_sheet import render


def test_sheet_contains_ten_distinct_decoded_frames(tmp_path):
    path = tmp_path / "swing.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25.0, (80, 120))
    if not writer.isOpened():
        pytest.skip("MJPG video encoder unavailable")
    for i in range(30):
        image = np.zeros((120, 80, 3), dtype=np.uint8)
        image[:, :, 0] = i * 7
        image[:, :, 1] = 255 - i * 7
        writer.write(image)
    writer.release()
    output = tmp_path / "contact.png"
    indices = list(range(2, 22, 2))
    render(path, indices, output)
    assert Image.open(output).size == (1600, 1050)
    manifest = json.loads(output.with_suffix(".json").read_text())
    assert [c["frame_index"] for c in manifest["checkpoints"]] == indices
    assert all(c["status"] == "unverified_candidate" for c in manifest["checkpoints"])
    assert manifest["coach_approved"] is False


def test_rejects_wrong_number_of_frames(tmp_path):
    with pytest.raises(ValueError, match="Exactly 10"):
        render(tmp_path / "missing.mp4", [1, 2], tmp_path / "out.png")
