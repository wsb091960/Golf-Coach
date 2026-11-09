"""Track 2D body landmarks in golf swing videos with MediaPipe Pose Landmarker.

Requires pip install mediapipe opencv-python-headless numpy and a local
pose_landmarker.task model. Clubhead/shaft tracking is NOT implemented.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

LANDMARKS = {"nose": 0, "left_shoulder": 11, "right_shoulder": 12,
             "left_elbow": 13, "right_elbow": 14, "left_wrist": 15,
             "right_wrist": 16, "left_hip": 23, "right_hip": 24,
             "left_knee": 25, "right_knee": 26, "left_ankle": 27,
             "right_ankle": 28}


def track_video(video_path: str, model_path: str, sample_every: int = 1,
                visibility_threshold: float = 0.55) -> dict:
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    if sample_every < 1:
        raise ValueError("sample_every must be >= 1")
    if not Path(model_path).is_file():
        raise FileNotFoundError(f"Pose model not found: {model_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        cap.release()
        raise ValueError("Invalid video FPS")
    width, height = int(cap.get(3)), int(cap.get(4))
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.VIDEO, num_poses=1)
    frames = []
    try:
        with vision.PoseLandmarker.create_from_options(options) as detector:
            index = 0
            while True:
                ok, bgr = cap.read()
                if not ok:
                    break
                if index % sample_every:
                    index += 1
                    continue
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = detector.detect_for_video(image, round(index * 1000 / fps))
                points = {}
                if result.pose_landmarks:
                    for name, idx in LANDMARKS.items():
                        p = result.pose_landmarks[0][idx]
                        if float(getattr(p, "visibility", 1.0) or 0) >= visibility_threshold:
                            points[name] = [round(p.x * width, 2), round(p.y * height, 2)]
                frames.append({"frame_index": index, "time": round(index / fps, 6),
                               "landmarks": points, "pose_detected": bool(points)})
                index += 1
    finally:
        cap.release()
    return {"video": video_path, "fps": fps, "width": width, "height": height,
            "frames": frames, "tracking_status": "pose_only",
            "club_tracking": "not_available",
            "warning": "P2/P6/P8 require separately validated club tracking."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", default="tracked.json")
    parser.add_argument("--sample-every", type=int, default=1)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(
        track_video(args.video, args.model, args.sample_every), indent=2))


if __name__ == "__main__":
    main()
