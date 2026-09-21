from pathlib import Path
from jinja2 import Environment

root = Path(__file__).resolve().parents[1]
router = (root / "app/routers/swing_analysis_workspace.py").read_text()
html = (root / "app/templates/swing_analysis_onform.html").read_text()
js = (root / "app/static/js/onform_screenshot_import.js").read_text()
session = (root / "app/templates/session_detail.html").read_text()

Environment().parse(html)
Environment().parse(session)

# 5.2.7 Body Data + sequence screenshot
assert 'id="onform-screenshot-file-3"' in html
assert "How Onform Body Data Works" in html
assert "Kinematic Sequence" in html

# 5.2.7A compact UI + obsolete Onform analysis cleanup
assert "compact-evidence-strip" in html
assert "compact-sequence-review" in html
assert "Import Onform Analysis" not in session
assert 'id="onform-analysis-modal"' not in session
assert "Open Swing Analysis" in session

# 5.2.7B persistence
assert "def _latest_onform_import" in router
assert '"latest_onform_import": latest_onform_import' in router
assert "Saved evidence" in html
assert "hydrateSavedImport" in js
assert "savedScreenshot(1)" in js

# 5.2.7C Student Primary Goal
assert "from app.models import Shot, Student, SwingAnalysis" in router
assert '"primary_goal": primary_goal' in router
assert 'id="student-primary-goal"' in html
assert "Coaching Goal Analysis" in html
assert "Student Primary Goal" in html
assert "updateCoachingGoalRead" in js
assert "requested push draw" not in js.lower()
assert "push-draw coaching read" not in html.lower()

print("phase 5.2.7C consolidated tests passed")
