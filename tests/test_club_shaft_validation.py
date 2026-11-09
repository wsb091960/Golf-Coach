import cv2
import numpy as np
from app.services.club_shaft_validation import validate_shaft_frame


def test_visible_shaft_has_edge_support():
    image = np.zeros((240,320,3), dtype=np.uint8)
    cv2.line(image, (80,40), (80,200), (255,255,255), 3)
    result = validate_shaft_frame(image, [80,40], [80,200], min_edge_fraction=.10)
    assert result["accepted"]


def test_blank_frame_rejected():
    image = np.zeros((240,320,3), dtype=np.uint8)
    result = validate_shaft_frame(image, [80,40], [80,200])
    assert not result["accepted"]


def test_outside_frame_rejected():
    image = np.zeros((240,320,3), dtype=np.uint8)
    assert validate_shaft_frame(image, [-5,40], [80,200])["reason"] == "outside_frame"
