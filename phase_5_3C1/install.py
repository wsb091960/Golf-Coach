from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil


ROOT = Path.cwd()
PACKAGE = Path(__file__).resolve().parent
PAYLOAD = PACKAGE / "app"
APP = ROOT / "app"

ASSET_REFS = (
    re.compile(r"(/static/css/header_removal\.css)(?:\?v=[^\"']+)?", re.I),
    re.compile(r"(/static/js/navigation_repair\.js)(?:\?v=[^\"']+)?", re.I),
)


def cache_bust(text: str) -> str:
    for pattern in ASSET_REFS:
        text = pattern.sub(r"\1?v=5.3C1", text)
    return text


def main() -> None:
    required = (
        APP / "templates/base.html",
        APP / "templates/coach_assistant.html",
        APP / "routers/coach_assistant.py",
        APP / "static/css/header_removal.css",
        APP / "static/js/navigation_repair.js",
    )
    for path in required:
        if not path.is_file():
            raise SystemExit(
                "Run this installer from /workspaces/Golf-Coach. Missing: "
                + str(path.relative_to(ROOT))
            )

    replacements = (
        (PAYLOAD / "templates/coach_assistant.html", APP / "templates/coach_assistant.html"),
        (PAYLOAD / "routers/coach_assistant.py", APP / "routers/coach_assistant.py"),
        (PAYLOAD / "static/css/coach_assistant.css", APP / "static/css/coach_assistant.css"),
        (PAYLOAD / "static/css/header_removal.css", APP / "static/css/header_removal.css"),
        (PAYLOAD / "static/js/navigation_repair.js", APP / "static/js/navigation_repair.js"),
        (PAYLOAD / "static/js/coach_assistant_tabs.js", APP / "static/js/coach_assistant_tabs.js"),
        (PAYLOAD / "static/img/golf-coach-dashboard-hero.png", APP / "static/img/golf-coach-dashboard-hero.png"),
    )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = ROOT / f"backup_5_3C1_{stamp}"
    destinations = {destination for _, destination in replacements}

    for destination in sorted(destinations):
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

    print("Phase 5.3C1 installed: expanded Coaching Assistant tabs are ready.")
    print("Navigation shell retained from the source-derived recovery.")
    print("Template cache references updated:", updated_count)
    print("Original files backed up in:", backup)
    print("Restart the server, then hard-refresh with Ctrl+Shift+R.")


if __name__ == "__main__":
    main()
