from pathlib import Path
from jinja2 import Environment

root = Path(__file__).resolve().parents[1]
router = (root/"app/routers/swing_analysis_workspace.py").read_text()
html = (root/"app/templates/swing_analysis_onform.html").read_text()
js = (root/"app/static/js/onform_screenshot_import.js").read_text()

Environment().parse(html)

assert 'is_verified = verified.lower() == "true"' in router
assert "Coach verification is required before saving screenshot metrics" not in router
assert '"status": "evidence_saved"' in router
assert '"status": "verified_committed"' in router
assert '"shot_committed": selected_shot is not None' in router
assert '"saved_import": _latest_onform_import(refreshed)' in router

assert "async function saveEvidenceDraft()" in js
assert "buildImportForm(false)" in js
assert "buildImportForm(true)" in js
assert "Metrics extracted. Saving screenshots as evidence" in js
assert "saved as evidence." in js
assert "Verified metrics saved to Shot Table." in js
assert "onform_screenshot_import.js?v=5.2.7G" in html

print("phase 5.2.7G evidence auto-save + verified shot commit tests passed")
