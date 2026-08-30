"""
WSBCO Golf Coach
Phase 5.2.2 installer

Run from:
/workspaces/Golf-Coach

What it does:
1. Verifies the Phase 5.2.2 files are in place.
2. Makes a timestamped backup of app/main.py.
3. Adds the Swing Analysis router to app/main.py if needed.
4. Runs Python syntax checks.

It does not modify the database schema.
Phase 5.2.1 must already be migrated.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import py_compile
import shutil


ROOT = Path("/workspaces/Golf-Coach")
MAIN = ROOT / "app" / "main.py"

REQUIRED = [
    ROOT / "app" / "models.py",
    ROOT / "app" / "swing_analysis_store.py",
    ROOT / "app" / "routers" / "swing_analysis.py",
]

for path in REQUIRED:
    if not path.exists():
        raise FileNotFoundError(
            f"Required file is missing: {path}"
        )


if not MAIN.exists():
    raise FileNotFoundError(
        f"main.py not found: {MAIN}"
    )


timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = MAIN.with_name(
    f"main_pre_phase_5_2_2_{timestamp}.py"
)

shutil.copy2(
    MAIN,
    backup,
)

print("Backup created:")
print(f"  {backup}")


text = MAIN.read_text()

import_line = (
    "from app.routers import swing_analysis as swing_analysis_router"
)

include_line = (
    "app.include_router(swing_analysis_router.router)"
)


changed = False

if import_line not in text:
    text = text.rstrip() + "\n\n" + import_line + "\n"
    changed = True

if include_line not in text:
    text = text.rstrip() + "\n" + include_line + "\n"
    changed = True


if changed:
    MAIN.write_text(text)
    print("Swing Analysis router added to app/main.py")
else:
    print("Swing Analysis router already installed.")


print()
print("Running syntax checks...")

for path in [
    ROOT / "app" / "models.py",
    ROOT / "app" / "swing_analysis_store.py",
    ROOT / "app" / "routers" / "swing_analysis.py",
    ROOT / "app" / "main.py",
]:
    py_compile.compile(
        str(path),
        doraise=True,
    )
    print(f"  OK: {path.relative_to(ROOT)}")


print()
print("Phase 5.2.2 installation complete.")
print()
print("Available endpoints:")
print("  POST /swing-analysis/video/{original_video_id}/create")
print("  GET  /swing-analysis/{analysis_id}")
print("  GET  /swing-analysis/session/{session_id}")
print("  POST /swing-analysis/{analysis_id}/onform/{onform_video_id}")
print("  POST /swing-analysis/{analysis_id}/shot/{shot_id}")
print("  PATCH /swing-analysis/{analysis_id}/checkpoint/{P1-P10}")
