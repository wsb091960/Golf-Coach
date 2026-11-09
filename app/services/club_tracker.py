"""Seeded golf-club optical-flow tracking. Requires opencv-python-headless and numpy."""
import cv2
import numpy as np
from math import atan2, degrees

def track_club(video_path, seed_frame, grip_xy, head_xy, max_fb_error=2.5, max_step_px=65):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or seed_frame < 0:
        raise ValueError("Invalid FPS or seed frame")
    cap.set(cv2.CAP_PROP_POS_FRAMES, seed_frame)
    ok, frame = cap.read()
    if not ok:
        raise ValueError("Cannot read seed frame")
    prev = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    points = np.asarray([grip_xy, head_xy], dtype=np.float32).reshape(2, 1, 2)
    options = dict(winSize=(31,31), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    records = []
    def record(index, pts, error):
        grip, head = pts.reshape(2, 2).tolist()
        records.append(dict(frame_index=index, time=index/fps, club_grip=grip, club_head=head,
            shaft_angle_deg=degrees(atan2(head[1]-grip[1],head[0]-grip[0])),
            fb_error_px=[float(v) for v in error], status="tracked"))
    record(seed_frame, points, [0,0])
    index = seed_frame
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            nxt, status, _ = cv2.calcOpticalFlowPyrLK(prev, gray, points, None, **options)
            if nxt is None or status is None or not np.all(status):
                break
            back, status_back, _ = cv2.calcOpticalFlowPyrLK(gray, prev, nxt, None, **options)
            if back is None or status_back is None or not np.all(status_back):
                break
            errors = np.linalg.norm(points.reshape(2,2)-back.reshape(2,2),axis=1)
            steps = np.linalg.norm(points.reshape(2,2)-nxt.reshape(2,2),axis=1)
            if np.any(errors>max_fb_error) or np.any(steps>max_step_px):
                break
            index += 1
            record(index, nxt, errors)
            points, prev = nxt, gray
    finally:
        cap.release()
    return dict(source="seeded_optical_flow", fps=fps, frames=records,
        last_tracked_frame=index, verified=False,
        warning="2D provisional tracking. Re-seed after blur or occlusion; no 3D or clubface inference.")
