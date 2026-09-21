from pathlib import Path

root = Path(__file__).resolve().parents[1]
html = (root / "app/templates/swing_analysis_onform.html").read_text()
js = (root / "app/static/js/onform_screenshot_import.js").read_text()
router = (root / "app/routers/swing_analysis_workspace.py").read_text()

assert "onform-screenshot-file-3" in html
assert "Onform Kinematic Sequence Review" in html
assert "Push-Draw Coaching Read" in html
assert "Green = within the typical professional range" in html
assert 'form.append("screenshot_3", third)' in js
assert 'form.append("sequence_json"' in js
assert "updatePushDrawRead" in js
assert "screenshot_3: UploadFile | None = File(None)" in router
assert '"kinematic_sequence": sequence' in router
assert '"phase": "5.2.7"' in router
print("phase 5.2.7 body data intelligence source-contract tests passed")
