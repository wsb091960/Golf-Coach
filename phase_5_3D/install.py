from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil


ROOT = Path.cwd()
PACKAGE = Path(__file__).resolve().parent
PAYLOAD = PACKAGE / "app"
APP = ROOT / "app"

VERSIONED_ASSETS = (
    "header_removal.css",
    "navigation_repair.js",
    "unified_workspace.css",
    "unified_workspace_tabs.js",
    "coach_assistant.css",
    "coach_assistant_tabs.js",
)


def cache_bust(text: str) -> str:
    for name in VERSIONED_ASSETS:
        pattern = re.compile(
            rf"(/static/(?:css|js)/{re.escape(name)})(?:\?v=[^\"']+)?",
            re.IGNORECASE,
        )
        text = pattern.sub(r"\1?v=5.3D", text)
    return text


def main() -> None:
    required = (
        APP / "templates/base.html",
        APP / "templates/dashboard.html",
        APP / "templates/students.html",
        APP / "templates/student_profile.html",
        APP / "templates/sessions.html",
        APP / "templates/session_detail.html",
        APP / "templates/garmin_import.html",
        APP / "templates/coach_assistant.html",
        APP / "templates/gapping.html",
        APP / "templates/biomechanics.html",
        APP / "routers/coach_assistant.py",
    )
    for path in required:
        if not path.is_file():
            raise SystemExit(
                "Run this installer from /workspaces/Golf-Coach. Missing: "
                + str(path.relative_to(ROOT))
            )

    relative_files = (
        "templates/base.html",
        "templates/dashboard.html",
        "templates/students.html",
        "templates/student_profile.html",
        "templates/sessions.html",
        "templates/session_detail.html",
        "templates/garmin_import.html",
        "templates/analysis.html",
        "templates/biomechanics.html",
        "templates/gapping.html",
        "templates/result.html",
        "templates/coach_assistant.html",
        "templates/swing_analysis_workspace.html",
        "templates/swing_analysis_onform.html",
        "templates/swing_analysis_p_position.html",
        "templates/swing_analysis_coaching.html",
        "templates/shots/list.html",
        "templates/shots/detail.html",
        "templates/shots/form.html",
        "routers/coach_assistant.py",
        "static/css/coach_assistant.css",
        "static/css/header_removal.css",
        "static/css/unified_workspace.css",
        "static/js/navigation_repair.js",
        "static/js/coach_assistant_tabs.js",
        "static/js/unified_workspace_tabs.js",
        "static/img/golf-coach-dashboard-hero.png",
    )
    replacements = tuple((PAYLOAD / relative, APP / relative) for relative in relative_files)

    for source, _ in replacements:
        if not source.is_file():
            raise SystemExit("Installer payload is incomplete: " + str(source))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = ROOT / f"backup_5_3D_{stamp}"
    for _, destination in replacements:
        if destination.exists():
            saved = backup / destination.relative_to(APP)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, saved)

    for source, destination in replacements:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    updated_count = 0
    for template in (APP / "templates").rglob("*.html"):
        source = template.read_text(encoding="utf-8")
        revised = cache_bust(source)
        if revised != source:
            template.write_text(revised, encoding="utf-8")
            updated_count += 1

    print("Phase 5.3D installed: unified page layout and nested tabs are ready.")
    print("Working backend routes and data are unchanged.")
    print("Template cache references updated:", updated_count)
    print("Original files backed up in:", backup)
    print("Restart the server, then hard-refresh with Ctrl+Shift+R.")


if __name__ == "__main__":
    main()
