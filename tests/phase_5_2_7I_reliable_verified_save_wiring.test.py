from pathlib import Path
from jinja2 import Environment
root = Path(__file__).resolve().parents[1]
html = (root/"app/templates/swing_analysis_onform.html").read_text()
js = (root/"app/static/js/onform_screenshot_import.js").read_text()
Environment().parse(html)
assert "async function commitVerifiedImport()" in js
assert 'saveButton.addEventListener("click"' in js
assert 'const workspaceSaveButton = document.getElementById("save-analysis")' in js
assert "event.stopImmediatePropagation()" in js
assert 'credentials: "same-origin"' in js
assert "if (!payload.shot_committed)" in js
assert "Saved draft metrics and screenshot evidence loaded" in js
assert "Verify &amp; Save Shot" in html
assert "onform_screenshot_import.js?v=5.2.7I" in html
print("phase 5.2.7I reliable verified save wiring tests passed")
