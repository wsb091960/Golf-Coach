from pathlib import Path

path = Path("app/templates/session_detail.html")
text = path.read_text(encoding="utf-8")

if 'id="topdown-flight-canvas"' in text:
    print("Top-down flight panel already exists.")
    raise SystemExit(0)

marker = '<article class="performance-card metric-card-panel">'

panel = '''
<article class="performance-card topdown-flight-card">
<div class="card-heading">
<div>
<span class="section-kicker">Ball Flight · Top Down</span>
<h2>Start Line + Curvature</h2>
</div>
</div>

<canvas
id="topdown-flight-canvas"
width="1000"
height="430"
></canvas>

<div class="simulation-note">
Top-down trajectory uses Garmin launch direction, measured offline distance when available, and curvature from spin axis or face-to-path.
</div>
</article>

'''

if marker not in text:
    raise SystemExit(
        "Could not find the selected-shot metrics panel. "
        "Install Phase 2.2 first."
    )

text = text.replace(marker, panel + marker, 1)
path.write_text(text, encoding="utf-8")

print("Added Top-Down Ball Flight panel.")
