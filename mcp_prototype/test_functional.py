"""Functional tests against a disposable SQLite database; never production."""
import os
import tempfile
import unittest
from pathlib import Path

class GolfMCPFunctionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="wsbco-mcp-golf-")
        cls.root = Path(cls.temp.name)
        (cls.root / ".wsbco-mcp-synthetic").touch()
        os.environ["WSBCO_MCP_DEV_ONLY"] = "1"
        os.environ["WSBCO_MCP_SYNTHETIC_DATA"] = "1"
        os.environ["WSBCO_MCP_TEST_DIR"] = str(cls.root)
        os.environ["DATABASE_URL"] = "sqlite:///" + str(cls.root / "golf.db")
        from app import models
        from app.database import Base, engine, SessionLocal
        Base.metadata.create_all(engine)
        cls.models, cls.SessionLocal = models, SessionLocal
        from mcp_prototype import server
        cls.server = server

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_student_list_and_latest_session_without_writes(self):
        from datetime import date
        m = self.models
        with self.SessionLocal() as db:
            db.add(m.Student(id="synthetic-1", first_name="Test", last_name="Golfer", status="Active"))
            db.add(m.CoachingSession(id="session-1", student_id="synthetic-1",
                                     session_date=date(2026, 1, 1), primary_club="7 iron"))
            db.add(m.Shot(id="shot-1", student_id="synthetic-1", session_id="session-1",
                          shot_number=1, club="7 iron", ball_speed=105.0, club_path=2.0))
            db.commit()
            from sqlalchemy import select, func
            before = tuple(db.scalar(select(func.count()).select_from(table)) for table in
                           (m.Student, m.CoachingSession, m.Shot))
        students = self.server.list_students()
        session = self.server.latest_session("synthetic-1")
        self.assertEqual(students[0]["student_id"], "synthetic-1")
        self.assertEqual(session["shots"][0]["club_path"], 2.0)
        self.assertNotIn("email", str(students))
        self.assertEqual(self.server.latest_session("not-found"), {"error": "Student not found"})
        with self.SessionLocal() as db:
            after = tuple(db.scalar(select(func.count()).select_from(table)) for table in
                          (m.Student, m.CoachingSession, m.Shot))
        self.assertEqual(before, after)
