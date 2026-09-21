from pathlib import Path
from jinja2 import Environment

root = Path(__file__).resolve().parents[1]
html = (root / "app/templates/swing_analysis_onform.html").read_text()
js = (root / "app/static/js/onform_screenshot_import.js").read_text()

Environment().parse(html)

assert "async function resolveEvidenceFile" in js
assert "await fetch(saved.url" in js
assert 'credentials: "same-origin"' in js
assert "const first = await resolveEvidenceFile(1, file1)" in js
assert "const second = await resolveEvidenceFile(2, file2)" in js
assert "const third = await resolveEvidenceFile(3, file3)" in js
assert "Choose both Onform screenshots for this swing." not in js
assert "Saved evidence was re-used; no file re-selection was required." in js
assert "onform_screenshot_import.js?v=5.2.7D" in html

print("phase 5.2.7D saved evidence re-extraction tests passed")
