from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil


ROOT = Path.cwd()
PACKAGE = Path(__file__).resolve().parent
PAYLOAD = PACKAGE / "app"
APP = ROOT / "app"

SHELL_CSS_REF = re.compile(
    r"(/static/css/header_removal\.css)(?:\?v=[^\"']+)?",
    flags=re.IGNORECASE,
)
NAV_SCRIPT_REF = re.compile(
    r"(/static/js/navigation_repair\.js)(?:\?v=[^\"']+)?",
    flags=re.IGNORECASE,
)


def cache_bust(text: str) -> str:
    text = SHELL_CSS_REF.sub(r"\1?v=5.3B7", text)
    return NAV_SCRIPT_REF.sub(r"\1?v=5.3B7", text)


def main() -> None:
    required = (
        APP / "templates" / "base.html",
        APP / "templates" / "students.html",
        APP / "templates" / "sessions.html",
        APP / "templates" / "garmin_import.html",
        APP / "static" / "css" / "dashboard.css",
        APP / "static" / "css" / "header_removal.css",
        APP / "static" / "js" / "navigation_repair.js",
        APP / "routers" / "coach_assistant.py",
    )
    for path in required:
        if not path.is_file():
            raise SystemExit(
                "Run this installer from /workspaces/Golf-Coach. Missing: "
                + str(path.relative_to(ROOT))
            )

    templates_to_update: list[tuple[Path, str]] = []
    for template in (APP / "templates").rglob("*.html"):
        source = template.read_text(encoding="utf-8")
        revised = cache_bust(source)
        if revised != source:
            templates_to_update.append((template, revised))

    replacements = (
        (PAYLOAD / "static/css/header_removal.css", APP / "static/css/header_removal.css"),
        (PAYLOAD / "static/js/navigation_repair.js", APP / "static/js/navigation_repair.js"),
        (PAYLOAD / "routers/coach_assistant.py", APP / "routers/coach_assistant.py"),
        (PAYLOAD / "templates/coach_assistant.html", APP / "templates/coach_assistant.html"),
    )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = ROOT / f"backup_5_3B7_{stamp}"
    destinations = {path for path, _ in templates_to_update}
    destinations.update(destination for _, destination in replacements)

    for destination in sorted(destinations):
        if destination.exists():
            saved = backup / destination.relative_to(APP)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, saved)

    for source, destination in replacements:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    # Re-read after replacements so the copied Coaching Assistant template also
    # receives the same cache token if it ever gains a direct shell reference.
    updated_count = 0
    for template in (APP / "templates").rglob("*.html"):
        source = template.read_text(encoding="utf-8")
        revised = cache_bust(source)
        if revised != source:
            template.write_text(revised, encoding="utf-8")
            updated_count += 1

    print("Phase 5.3B7 installed: source-derived page-shell recovery complete.")
    print("Template cache references updated:", updated_count)
    print("Original files backed up in:", backup)
    print("Restart the server, then hard-refresh with Ctrl+Shift+R.")


if __name__ == "__main__":
    main()
