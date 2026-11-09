"""Evaluate frame-independent club candidate detection against held-out coach annotations.

Input JSON: {"fps": 58.319, "seeds": [{"frame_index": 270,
"club_grip": [x,y], "club_head": [x,y]}, ...], "verified": true}.
No accuracy score is emitted for unverified labels.
"""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from app.services.club_reacquisition import shaft_candidates


def evaluate(video_path, annotations, output_dir):
    if annotations.get("verified") is not True:
        raise ValueError("Coach-verified annotations required for accuracy evaluation")
    rows = annotations.get("seeds", [])
    if len(rows) < 2:
        raise ValueError("At least two verified keyframes required")
    ids = [r["frame_index"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate frame indices")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError("Cannot read video")
    results = []
    try:
        for row in sorted(rows, key=lambda r: r["frame_index"]):
            idx = row["frame_index"]
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                results.append({"frame_index": idx, "status": "unreadable"})
                continue
            grip, head = row["club_grip"], row["club_head"]
            candidates = shaft_candidates(frame, grip)
            if not candidates:
                status, error, candidate = "no_candidates", None, None
            else:
                # Held-out head is NEVER supplied as a selection hint.
                candidate = candidates[0]
                error = float(np.linalg.norm(
                    np.asarray(candidate["clubhead_candidate"]) - np.asarray(head)))
                status = "candidate_proposed"
            results.append({"frame_index": idx, "status": status,
                            "candidate_count": len(candidates),
                            "top_candidate_error_px": round(error, 2) if error is not None else None})
            overlay = frame.copy()
            g = tuple(map(int, grip))
            h = tuple(map(int, head))
            cv2.circle(overlay, g, 7, (0, 255, 0), 2)
            cv2.circle(overlay, h, 9, (255, 0, 0), 2)
            if candidate:
                p = tuple(map(int, candidate["clubhead_candidate"]))
                cv2.circle(overlay, p, 10, (0, 0, 255), 2)
                cv2.line(overlay, g, p, (0, 255, 255), 2)
            caption = (f"Frame {idx} | candidate error {error:.1f}px"
                       if error is not None else f"Frame {idx} | no candidate")
            cv2.putText(overlay, caption, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, .7, (255,255,255), 2)
            cv2.imwrite(str(out / f"frame_{idx:05d}.jpg"), overlay)
    finally:
        cap.release()
    errors = [r["top_candidate_error_px"] for r in results
              if r.get("top_candidate_error_px") is not None]
    report = {"verified_ground_truth": True, "evaluated_frames": len(results),
              "frames_with_candidates": len(errors),
              "coverage": len(errors)/len(results),
              "median_top_candidate_error_px": float(np.median(errors)) if errors else None,
              "within_15px": sum(e <= 15 for e in errors)/len(results),
              "per_frame": results,
              "note": "Coach-verified labels used only for scoring, not candidate selection."}
    (out/"evaluation.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("annotations")
    parser.add_argument("--output", default="club_evaluation")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.video,
        json.loads(Path(args.annotations).read_text()), args.output), indent=2))
