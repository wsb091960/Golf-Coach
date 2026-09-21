WSBCO Golf Coach — Phase 5.3C2
Session-to-Assessment Title Flow

Install from /workspaces/Golf-Coach:

  unzip -o Golf_Coach_Phase_5_3C2_Assessment_Title_Flow.zip
  python phase_5_3C2/install.py
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Then hard-refresh the browser with Ctrl+Shift+R.

What changes:
- Assessment titles now follow the linked session type shown on the Sessions
  page, such as Practice, Playing Lesson, or Club Evaluation.
- A custom session name is appended when present, such as Practice · Driver Work.
- Existing assessments are corrected automatically when displayed.
- The active assessment title appears above Five Practice Drills, Video Library,
  and Coach's Corner.
- The default Coaching Assistant view remains a compact prompt workspace.
- Five Practice Drills, Video Library, and Coach's Corner are separate tabs.
- Coach's Corner contains the analysis, coaching priority, student explanation,
  ball-flight cue, pass/fail test, and reassessment guidance.
- After analysis, Five Practice Drills opens first.
- Visual, body-screen, evidence, and assessment tools remain separated into tabs.
- The gold golfer logo appears in a smaller Coaching Assistant hero.
- Every saved or new plan includes topic-specific YouTube discovery links for
  MyTPI, Clay Ballard / Top Speed Golf, and Eric Cogorno Golf.
- Existing assessments receive the video links without another API call.
- The Phase 5.3B7 navigation and page-shell recovery remains included.
- Session cleanup and permanent session deletion remain available under Assessments.

Video note:
The app intentionally creates instructor-and-topic YouTube search links rather than
asking AI to invent a specific watch URL. This prevents broken or fabricated links
and lets the coach choose the best current video for the student.
