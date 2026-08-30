from __future__ import annotations

from datetime import datetime
from pathlib import Path
import py_compile
import shutil

ROOT = Path("/workspaces/Golf-Coach")
MAIN = ROOT / "app" / "main.py"
TEMPLATE = ROOT / "app" / "templates" / "swing_analysis_workspace.html"
ROUTER = ROOT / "app" / "routers" / "swing_analysis_assist.py"

for path in [MAIN, TEMPLATE, ROUTER]:
    if not path.exists():
        raise FileNotFoundError(f"Required file is missing: {path}")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
main_backup = MAIN.with_name(f"main_pre_phase_5_2_4_{timestamp}.py")
template_backup = TEMPLATE.with_name(
    f"swing_analysis_workspace_pre_phase_5_2_4_{timestamp}.html"
)

shutil.copy2(MAIN, main_backup)
shutil.copy2(TEMPLATE, template_backup)

print("Backups created:")
print(f"  {main_backup}")
print(f"  {template_backup}")

# Wire router into main.py.
main_text = MAIN.read_text()
import_line = "from app.routers import swing_analysis_assist as swing_analysis_assist_router"
include_line = "app.include_router(swing_analysis_assist_router.router)"

changed = False
if import_line not in main_text:
    main_text = main_text.rstrip() + "\n\n" + import_line + "\n"
    changed = True
if include_line not in main_text:
    main_text = main_text.rstrip() + "\n" + include_line + "\n"
    changed = True
if changed:
    MAIN.write_text(main_text)
    print("P1-P10 Assist router added to app/main.py.")
else:
    print("P1-P10 Assist router already installed.")

# Patch workspace template.
text = TEMPLATE.read_text()

css_marker = '<link rel="stylesheet" href="/static/css/swing_analysis_workspace.css">'
css_line = '<link rel="stylesheet" href="/static/css/swing_analysis_assist.css">'
if css_line not in text:
    if css_marker not in text:
        raise RuntimeError("Could not find workspace CSS link.")
    text = text.replace(css_marker, css_marker + "\n    " + css_line, 1)

assist_panel = '''
            <div class="checkpoint-assist-panel">
                <span class="section-kicker">Auto Assist</span>
                <h3>P1–P10 Timing Assistant</h3>
                <p>
                    Mark P1 and P10 from the original video, choose the capture
                    frame rate, then estimate P2–P9. Every estimate remains coach-adjustable.
                </p>

                <div class="checkpoint-assist-grid">
                    <label>
                        <span>P1 Time (sec)</span>
                        <input id="assist-p1-time" type="number" step="0.001"
                               value="{{ analysis.checkpoints[0].time_seconds if analysis.checkpoints and analysis.checkpoints[0].time_seconds is not none else '' }}">
                    </label>

                    <label>
                        <span>P10 Time (sec)</span>
                        <input id="assist-p10-time" type="number" step="0.001"
                               value="{{ analysis.checkpoints[9].time_seconds if analysis.checkpoints|length >= 10 and analysis.checkpoints[9].time_seconds is not none else '' }}">
                    </label>

                    <label>
                        <span>Video FPS</span>
                        <select id="assist-fps">
                            <option value="30">30 fps</option>
                            <option value="60">60 fps</option>
                            <option value="120" selected>120 fps</option>
                            <option value="240">240 fps</option>
                        </select>
                    </label>

                    <label>
                        <span>Method</span>
                        <input value="Coach-marked timing estimate" readonly>
                    </label>
                </div>

                <label class="checkpoint-assist-check">
                    <input id="assist-overwrite" type="checkbox">
                    <span>Overwrite already-set P2–P9 times</span>
                </label>

                <div class="checkpoint-assist-actions">
                    <button type="button" class="button button-secondary" id="assist-mark-p1">
                        Mark Current Time as P1
                    </button>
                    <button type="button" class="button button-secondary" id="assist-mark-p10">
                        Mark Current Time as P10
                    </button>
                    <button type="button" class="button button-secondary" id="assist-use-video-range">
                        Use Full Video Range
                    </button>
                    <button type="button" class="button button-primary" id="assist-seed-checkpoints">
                        Auto-Seed P1–P10
                    </button>
                    <button type="button" class="button button-secondary" id="assist-derive-x-factor">
                        Recalculate X-Factor
                    </button>
                </div>

                <strong id="assist-status"></strong>
            </div>
'''

if 'id="assist-seed-checkpoints"' not in text:
    marker = '            <div\n                class="p-position-strip"'
    pos = text.find(marker)
    if pos == -1:
        pos = text.find('<div class="p-position-strip"')
    if pos == -1:
        raise RuntimeError("Could not locate P-position strip.")
    text = text[:pos] + assist_panel + "\n" + text[pos:]

script_marker = '<script src="/static/js/swing_analysis_workspace.js?v=5.2.3"></script>'
script_line = '<script src="/static/js/swing_analysis_assist.js?v=5.2.4"></script>'
if script_line not in text:
    if script_marker not in text:
        raise RuntimeError("Could not find Phase 5.2.3 workspace script.")
    text = text.replace(script_marker, script_marker + "\n" + script_line, 1)

TEMPLATE.write_text(text)
print("P1-P10 Auto Assist controls added to workspace.")

print()
print("Running syntax checks...")
for path in [
    ROOT / "app" / "routers" / "swing_analysis_assist.py",
    ROOT / "app" / "routers" / "swing_analysis_workspace.py",
    ROOT / "app" / "routers" / "swing_analysis.py",
    ROOT / "app" / "swing_analysis_store.py",
    ROOT / "app" / "models.py",
    ROOT / "app" / "main.py",
]:
    py_compile.compile(str(path), doraise=True)
    print(f"  OK: {path.relative_to(ROOT)}")

verify = TEMPLATE.read_text()
if 'id="assist-seed-checkpoints"' not in verify:
    raise RuntimeError("Auto Assist UI verification failed.")
if "swing_analysis_assist.js?v=5.2.4" not in verify:
    raise RuntimeError("Auto Assist JS verification failed.")

print()
print("Phase 5.2.4 installation complete.")
print("Workflow: mark P1 -> mark P10 -> select FPS -> Auto-Seed P1-P10 -> verify each checkpoint.")
