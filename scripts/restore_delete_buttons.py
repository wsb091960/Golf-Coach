from __future__ import annotations

from pathlib import Path


def find_root() -> Path:
    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        if (candidate / "app" / "templates").is_dir():
            return candidate
    raise SystemExit("Could not locate the WSBCO Golf Coach project root.")


ROOT = find_root()
TEMPLATES = ROOT / "app" / "templates"


STUDENT_DELETE = '''
<section class="content-card" style="border-color:#efc9c5;background:#fffafa">
<div class="panel-header">
<div><div class="panel-eyebrow" style="color:#a33b32">Danger Zone</div><h2>Delete Student</h2></div>
</div>
<p class="page-subtitle">Permanently deletes this student and all associated sessions and shots.</p>
<form method="post" action="/students/{{ student.id }}/delete" onsubmit="return confirm('Delete {{ student.name|e }} and all associated sessions and shots? This cannot be undone.')">
<button class="button" type="submit" style="background:#b33f35;color:#fff;border-color:#b33f35">Delete Student</button>
</form>
</section>
'''


SESSION_DELETE = '''
<section class="performance-card" style="border-color:#efc9c5;background:#fffafa">
<div class="card-heading"><div><span class="section-kicker" style="color:#a33b32">Danger Zone</span><h2>Delete Session</h2></div></div>
<p class="simulation-note">Permanently deletes this session and its imported shots. The student and other sessions remain.</p>
<form method="post" action="/sessions/{{ session.id }}/delete" onsubmit="return confirm('Delete this session and all of its imported shots? This cannot be undone.')">
<button class="button" type="submit" style="background:#b33f35;color:#fff;border-color:#b33f35">Delete Session</button>
</form>
</section>
'''


def insert_once(path: Path, unique: str, marker: str, block: str) -> None:
    if not path.exists():
        raise SystemExit(f"Template not found: {path}")
    text = path.read_text(encoding="utf-8")
    if unique in text:
        return
    if marker not in text:
        raise SystemExit(f"Could not find insertion point in {path.name}; no change was made.")
    path.write_text(text.replace(marker, block + marker, 1), encoding="utf-8")


def main() -> None:
    insert_once(
        TEMPLATES / "student_profile.html",
        'action="/students/{{ student.id }}/delete"',
        "</main>",
        STUDENT_DELETE,
    )
    session_path = TEMPLATES / "session_detail.html"
    session_text = session_path.read_text(encoding="utf-8") if session_path.exists() else ""
    marker = '<div class="modal-backdrop"' if '<div class="modal-backdrop"' in session_text else "</main>"
    insert_once(
        session_path,
        'action="/sessions/{{ session.id }}/delete"',
        marker,
        SESSION_DELETE,
    )
    print("Restored Delete Student and Delete Session buttons.")


if __name__ == "__main__":
    main()

