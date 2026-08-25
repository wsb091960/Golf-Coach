from __future__ import annotations

from pathlib import Path


def find_root() -> Path:
    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        if (candidate / "app" / "routers" / "sessions.py").is_file():
            return candidate
    raise SystemExit("Could not locate the WSBCO Golf Coach project root.")


ROOT = find_root()
ROUTER = ROOT / "app" / "routers" / "sessions.py"
TEMPLATE = ROOT / "app" / "templates" / "session_detail.html"
CSS = ROOT / "app" / "static" / "css" / "session_performance.css"


def patch_router() -> None:
    text = ROUTER.read_text(encoding="utf-8")
    if "'club_count':club_count" in text or '"club_count": club_count' in text:
        return

    if "from collections import Counter" not in text:
        text = text.replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\nfrom collections import Counter\n",
            1,
        )

    marker = "    def avg(field):"
    calculation = '''    club_counts = Counter(
        str(row.get('club')).strip()
        for row in included
        if str(row.get('club') or '').strip()
    )
    club_count = len(club_counts)
    dominant_club = club_counts.most_common(1)[0][0] if club_counts else None
    if club_count == 0:
        club_summary = '—'
    elif club_count == 1:
        club_summary = dominant_club
    else:
        club_summary = f'Mixed · {club_count} Clubs'
'''
    if marker not in text:
        raise SystemExit("Could not locate session metric calculation; no router change was made.")
    text = text.replace(marker, calculation + marker, 1)

    old = "'session_metrics':{'shots':len(included),'carry':avg('carry_distance')"
    new = "'session_metrics':{'shots':len(included),'club_count':club_count,'club_summary':club_summary,'dominant_club':dominant_club,'carry':avg('carry_distance')"
    if old not in text:
        raise SystemExit("Could not locate session_metrics context; no router change was made.")
    ROUTER.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_template() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    if "session_metrics.club_summary" not in text:
        old = '<div class="kpi"><span>Primary Club</span><strong>{{ session.primary_club or "—" }}</strong></div>'
        new = '<div class="kpi"><span>Session Clubs</span><strong>{{ session_metrics.club_summary }}</strong></div><div class="kpi"><span>Dominant Club</span><strong>{{ session_metrics.dominant_club or "—" }}</strong></div>'
        if old not in text:
            raise SystemExit("Could not locate the Primary Club KPI; no template change was made.")
        text = text.replace(old, new, 1)

    text = text.replace(
        "value=\"{{ session.primary_club or '' }}\" placeholder=\"Club\"",
        "value=\"{{ session_metrics.dominant_club or session.primary_club or '' }}\" placeholder=\"Club\"",
    )
    TEMPLATE.write_text(text, encoding="utf-8")


def patch_css() -> None:
    text = CSS.read_text(encoding="utf-8")
    text = text.replace(
        "grid-template-columns:repeat(8,minmax(105px,1fr))",
        "grid-template-columns:repeat(9,minmax(105px,1fr))",
        1,
    )
    CSS.write_text(text, encoding="utf-8")


def main() -> None:
    patch_router()
    patch_template()
    patch_css()
    print("Added Mixed club summary and separate Dominant Club KPI.")


if __name__ == "__main__":
    main()

