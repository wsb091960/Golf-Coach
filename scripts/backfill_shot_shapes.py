from __future__ import annotations
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Shot

def derive(shot: Shot) -> str:
    ftp = shot.face_to_path
    if ftp is None and shot.club_face is not None and shot.club_path is not None:
        ftp = shot.club_face - shot.club_path
    if ftp is not None:
        if abs(ftp) <= 1.0:
            return "Straight"
        return "Left Curve" if ftp < -1.0 else "Right Curve"
    if shot.spin_axis is not None:
        if abs(shot.spin_axis) <= 2.0:
            return "Straight"
        return "Left Curve" if shot.spin_axis < -2.0 else "Right Curve"
    return "Unknown"

def main() -> None:
    db = SessionLocal()
    try:
        rows = db.scalars(select(Shot)).all()
        updated = 0
        for shot in rows:
            if str(shot.shot_shape or "").strip():
                continue
            shot.shot_shape = derive(shot)
            updated += 1
        db.commit()
        print(f"Shot shapes backfilled: {updated}")
        print(f"Total shots checked: {len(rows)}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
