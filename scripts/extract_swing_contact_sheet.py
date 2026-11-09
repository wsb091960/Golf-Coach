"""Generate a ten-frame contact sheet from a video on the server.

Usage:
 python scripts/extract_swing_contact_sheet.py video.mp4 --frames 235,255,270,288,304,310,313,318,325,340 --output dtl.png

The frame indices MUST be reviewed/approved by a coach. This tool deliberately
does not claim that equidistant frames or heuristics are P-position detection.
Requires opencv-python and Pillow. No browser seeking or FPS arithmetic.
"""
import argparse
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont

LABELS = [
    "P1 Address", "P2 Shaft parallel back", "P3 Lead arm parallel back",
    "P4 Top", "P5 Lead arm parallel down", "P6 Shaft parallel down",
    "P7 Impact", "P8 Shaft parallel through", "P9 Trail arm parallel through",
    "P10 Finish",
]


def render(video_path: Path, frames: list[int], output: Path) -> None:
    if len(frames) != 10 or any(f < 0 for f in frames):
        raise ValueError("Exactly 10 nonnegative decoded frame indices are required")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {video_path}")
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if any(f >= count for f in frames):
        raise ValueError(f"Frame index exceeds available {count} frames")
    sheet = Image.new("RGB", (1600, 1050), "#152528")
    draw = ImageDraw.Draw(sheet)
    evidence = []
    try:
        for i, index in enumerate(frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, bgr = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode frame {index}")
            actual = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            if actual != index:
                raise RuntimeError(f"Requested frame {index}, decoded frame {actual}")
            time_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            img.thumbnail((304, 440))
            x = (i % 5) * 320 + (320 - img.width) // 2
            y = (i // 5) * 525 + 36
            sheet.paste(img, (x, y))
            draw.text(((i % 5) * 320 + 8, (i // 5) * 525 + 8), LABELS[i], fill="#f3d183")
            draw.text(((i % 5) * 320 + 8, (i // 5) * 525 + 486),
                      f"Decoded frame {index} | {time_ms / 1000:.3f}s | unverified",
                      fill="#e6eeee")
            evidence.append({"position": f"P{i+1}", "frame_index": index,
                             "timestamp_seconds": time_ms / 1000,
                             "status": "unverified_candidate"})
    finally:
        cap.release()
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    output.with_suffix(".json").write_text(
        json.dumps({"video": str(video_path), "source": "decoded_server_frames",
                    "coach_approved": False, "checkpoints": evidence}, indent=2)
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("video", type=Path)
    p.add_argument("--frames", required=True,
                   help="Ten comma-separated decoded frame indices, P1 through P10")
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    render(a.video, [int(s.strip()) for s in a.frames.split(",")], a.output)
