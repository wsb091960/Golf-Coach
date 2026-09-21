from pathlib import Path
from jinja2 import Environment

root = Path(__file__).resolve().parents[1]
router = (root / "app/routers/swing_analysis_workspace.py").read_text()
html = (root / "app/templates/swing_analysis_onform.html").read_text()

Environment().parse(html)

assert 'shot_id == "__new__"' in router
assert "selected_shot = Shot(" in router
assert "shot_number=next_shot_number" in router
assert 'source="Onform Screenshot"' in router
assert 'selected_shot.smash_factor = round(' in router
assert '"phase": "5.2.7F"' in router

assert "Record Launch / Garmin Metrics In Shot Table" in html
assert 'value="__new__"' in html
assert "Create new Shot Table record" in html
assert "Update Shot {{ shot.shot_number }}" in html
assert "Side Spin remains screenshot evidence and is not converted to Spin Axis." in html

print("phase 5.2.7F shot table integration tests passed")
