WSBCO Golf Coach — Phase 5.3D
Unified Layout and Nested Navigation

Install from /workspaces/Golf-Coach:

  unzip -o Golf_Coach_Phase_5_3D_Unified_Layout_Nested_Tabs.zip
  python phase_5_3D/install.py
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Then hard-refresh the browser with Ctrl+Shift+R.

What changes:
- All primary pages use the Coaching Assistant green-and-gold visual system.
- Dashboard, Students, Student Profile, Sessions, and Garmin Import use the
  same shared base shell and left navigation.
- Session Detail and swing-analysis pages retain their working controls while
  adopting the shared hero, cards, responsive width, navigation, and tabs.
- Students: Student Directory / Add Student.
- Student Profile: Overview / Sessions / Account.
- Sessions: Recent Sessions / Create Session.
- Garmin & Onform Import: Garmin R10 CSV / Onform Workflow.
- Session Detail: Overview / Charts / Shots / Videos / Notes.
- Gapping: Bag Map / Distance Ladder.
- Biomechanics: Setup / Video & Priorities / Measurements / Coaching Process.
- P-Position: Swing Video / P1-P10 Checkpoints.
- Coaching Analysis: Ball Flight / TGM / TPI / Measurements / Priorities.
- Shot List: Session Summary / Shot Table.
- Shot Detail: Metrics / Launch & Distance / Speed & Efficiency / Club Delivery /
  Notes & Actions.
- Add or Edit Shot: Shot Information / Distance / Speed / Launch / Club Delivery.
- The earlier Coaching Assistant drill, video, Coach's Corner, title-flow,
  navigation, and session-deletion fixes remain included.

Safety:
- No database migration is performed.
- No students, sessions, shots, assessments, videos, or notes are deleted.
- Every replaced source file is copied to a timestamped backup folder first.
- Historical .pre_* and backup templates are not changed.
