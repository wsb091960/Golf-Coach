"""Local-only, read-only MCP prototype. Not mounted in production."""
from mcp.server import MCPServer
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Student, CoachingSession, Shot

mcp = MCPServer("WSBCO Golf Coach - local read-only prototype")

@mcp.tool()
def list_students(limit: int = 10) -> list[dict]:
    """List basic student profiles; exclude contact information."""
    limit = max(1, min(int(limit), 25))
    with SessionLocal() as db:
        students = db.scalars(select(Student).order_by(
            Student.created_at.desc()).limit(limit)).all()
        return [{"student_id": s.id, "name": s.name, "status": s.status,
                 "handedness": s.handedness} for s in students]

@mcp.tool()
def latest_session(student_id: str) -> dict:
    """Return latest session and up to 30 saved shot metrics, without modifying records."""
    with SessionLocal() as db:
        student = db.get(Student, student_id)
        if student is None:
            return {"error": "Student not found"}
        session = db.scalar(select(CoachingSession).where(
            CoachingSession.student_id == student_id
        ).order_by(CoachingSession.session_date.desc(),
                   CoachingSession.created_at.desc()).limit(1))
        if session is None:
            return {"student_id": student_id, "session": None, "shots": []}
        shots = db.scalars(select(Shot).where(Shot.session_id == session.id)
                           .order_by(Shot.shot_number).limit(30)).all()
        return {
            "student_id": student_id,
            "session": {"id": session.id, "date": session.session_date.isoformat(),
                        "club": session.primary_club, "type": session.session_type},
            "shots": [{"number": s.shot_number, "club": s.club,
                       "ball_speed": s.ball_speed, "club_speed": s.club_speed,
                       "club_path": s.club_path, "club_face": s.club_face,
                       "face_to_path": s.face_to_path, "shot_shape": s.shot_shape}
                      for s in shots]
        }

if __name__ == "__main__":
    mcp.run()
