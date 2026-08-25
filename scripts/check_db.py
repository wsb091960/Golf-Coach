"""
Display persistent WSBCO Golf Coach database counts.
"""

from sqlalchemy import func, select

from app.database import SessionLocal, DATABASE_PATH
from app.models import CoachingSession, Shot, Student


def main():
    db = SessionLocal()
    try:
        students = db.scalar(
            select(func.count(Student.id))
        ) or 0
        sessions = db.scalar(
            select(func.count(CoachingSession.id))
        ) or 0
        shots = db.scalar(
            select(func.count(Shot.id))
        ) or 0

        print(f"Database: {DATABASE_PATH}")
        print(f"Students: {students}")
        print(f"Sessions: {sessions}")
        print(f"Shots: {shots}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
