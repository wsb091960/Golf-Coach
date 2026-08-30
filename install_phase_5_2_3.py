"""
WSBCO Golf Coach
Phase 5.2.3 installer

Adds:
    app/routers/swing_analysis_workspace.py
    app/templates/swing_analysis_workspace.html
    app/static/css/swing_analysis_workspace.css
    app/static/js/swing_analysis_workspace.js

Wires the workspace router into app/main.py.
Does not alter the database schema.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import py_compile
import shutil


ROOT = Path("/workspaces/Golf-Coach")
MAIN = ROOT / "app" / "main.py"

required = [
    ROOT / "app" / "routers" / "swing_analysis_workspace.py",
    ROOT / "app" / "templates" / "swing_analysis_workspace.html",
    ROOT / "app" / "static" / "css" / "swing_analysis_workspace.css",
    ROOT / "app" / "static" / "js" / "swing_analysis_workspace.js",
]

for path in required:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing Phase 5.2.3 file: {path}"
        )

if not MAIN.exists():
    raise FileNotFoundError(
        f"main.py not found: {MAIN}"
    )


timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

backup = MAIN.with_name(
    f"main_pre_phase_5_2_3_{timestamp}.py"
)

shutil.copy2(
    MAIN,
    backup,
)

print("Backup created:")
print(f"  {backup}")


text = MAIN.read_text()

import_line = (
    "from app.routers import "
    "swing_analysis_workspace as "
    "swing_analysis_workspace_router"
)

include_line = (
    "app.include_router("
    "swing_analysis_workspace_router.router"
    ")"
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
    print(
        "Swing Analysis Workspace router "
        "added to app/main.py"
    )
else:
    print(
        "Swing Analysis Workspace router "
        "already installed."
    )


print()
print("Running syntax checks...")

for path in [
    ROOT / "app" / "routers" / "swing_analysis_workspace.py",
    ROOT / "app" / "swing_analysis_store.py",
    ROOT / "app" / "models.py",
    ROOT / "app" / "main.py",
]:
    py_compile.compile(
        str(path),
        doraise=True,
    )

    print(
        f"  OK: {path.relative_to(ROOT)}"
    )


print()
print("Phase 5.2.3 installation complete.")
print()
print("Workspace route:")
print(
    "  GET /swing-analysis/{analysis_id}/workspace"
)
