"""Synthetic regression tests for frame-independent shaft candidates."""
import unittest
import cv2
import numpy as np
from app.services.club_reacquisition import shaft_candidates


class ReacquisitionTests(unittest.TestCase):
    def test_detects_synthetic_shaft_near_grip(self):
        img = np.zeros((240, 320, 3), np.uint8)
        cv2.line(img, (70, 200), (230, 55), (255, 255, 255), 3)
        out = shaft_candidates(img, (70, 200))
        self.assertTrue(out)
        self.assertTrue(any(
            np.linalg.norm(np.array(c["clubhead_candidate"])-[230, 55]) < 15
            for c in out))
        self.assertTrue(all(c["verified"] is False for c in out))

    def test_no_line_does_not_invent_head(self):
        self.assertEqual(
            shaft_candidates(np.zeros((200, 200, 3), np.uint8), (40, 40)), [])

    def test_rejects_invalid_grip(self):
        with self.assertRaises(ValueError):
            shaft_candidates(
                np.zeros((200, 200, 3), np.uint8), [float("nan"), 4])


if __name__ == "__main__":
    unittest.main()
