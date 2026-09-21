from pathlib import Path
from jinja2 import Environment
p = Path(__file__).resolve().parents[1] / "app/templates/session_detail.html"
s = p.read_text()
Environment().parse(s)
assert "Import Onform Analysis" not in s
assert 'id="onform-analysis-modal"' not in s
assert 'class="onform-analysis-list"' not in s
assert "Open Swing Analysis" in s
assert "Download / Share" in s
print("phase 5.2.7A session detail repair tests passed")
