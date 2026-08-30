from __future__ import annotations

from datetime import datetime
from pathlib import Path
import py_compile
import shutil

ROOT = Path("/workspaces/Golf-Coach")

MAIN = ROOT / "app" / "main.py"
TEMPLATE = ROOT / "app" / "templates" / "session_detail.html"
ROUTER = ROOT / "app" / "routers" / "swing_analysis_launch.py"

for path in [MAIN, TEMPLATE, ROUTER]:
    if not path.exists():
        raise FileNotFoundError(f"Required file is missing: {path}")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

main_backup = MAIN.with_name(f"main_pre_phase_5_2_3A_{timestamp}.py")
template_backup = TEMPLATE.with_name(
    f"session_detail_pre_phase_5_2_3A_{timestamp}.html"
)

shutil.copy2(MAIN, main_backup)
shutil.copy2(TEMPLATE, template_backup)

print("Backups created:")
print(f"  {main_backup}")
print(f"  {template_backup}")

# main.py
main_text = MAIN.read_text()

import_line = (
    "from app.routers import swing_analysis_launch "
    "as swing_analysis_launch_router"
)
include_line = "app.include_router(swing_analysis_launch_router.router)"

changed = False

if import_line not in main_text:
    main_text = main_text.rstrip() + "\n\n" + import_line + "\n"
    changed = True

if include_line not in main_text:
    main_text = main_text.rstrip() + "\n" + include_line + "\n"
    changed = True

if changed:
    MAIN.write_text(main_text)
    print("Swing Analysis launch router added to app/main.py")
else:
    print("Swing Analysis launch router already installed.")

# session_detail.html
template_text = TEMPLATE.read_text()

if 'href="/swing-analysis/video/{{ video.id }}/open"' not in template_text:
    marker = 'href="/sessions/{{ session.id }}/videos/{{ video.id }}/download"'
    marker_pos = template_text.find(marker)

    if marker_pos == -1:
        raise RuntimeError(
            "Could not find the Original Swing Download / Share button."
        )

    anchor_start = template_text.rfind("<a", 0, marker_pos)
    anchor_end = template_text.find("</a>", marker_pos)

    if anchor_start == -1 or anchor_end == -1:
        raise RuntimeError(
            "Could not locate the Original Swing download anchor."
        )

    anchor_end += len("</a>")

    open_button = '''
                                    <a
                                        class="table-action"
                                        href="/swing-analysis/video/{{ video.id }}/open"
                                    >
                                        Open Swing Analysis
                                    </a>
'''

    template_text = (
        template_text[:anchor_end]
        + "\n"
        + open_button
        + template_text[anchor_end:]
    )

    TEMPLATE.write_text(template_text)
    print("Open Swing Analysis button added to Original Swing cards.")
else:
    print("Open Swing Analysis button already present.")

print()
print("Running syntax checks...")

for path in [
    ROOT / "app" / "routers" / "swing_analysis_launch.py",
    ROOT / "app" / "routers" / "swing_analysis.py",
    ROOT / "app" / "routers" / "swing_analysis_workspace.py",
    ROOT / "app" / "swing_analysis_store.py",
    ROOT / "app" / "models.py",
    ROOT / "app" / "main.py",
]:
    py_compile.compile(str(path), doraise=True)
    print(f"  OK: {path.relative_to(ROOT)}")

template_check = TEMPLATE.read_text()

if 'href="/swing-analysis/video/{{ video.id }}/open"' not in template_check:
    raise RuntimeError("Session Detail button verification failed.")

print()
print("Phase 5.2.3A installation complete.")
print()
print(
    "Workflow: Session -> Original Swing -> Open Swing Analysis "
    "-> Coaching Analysis Workspace"
)
