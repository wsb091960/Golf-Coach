from __future__ import annotations

from pathlib import Path


def find_root() -> Path:
    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        if (
            (candidate / "app" / "templates" / "session_detail.html").is_file()
            and (candidate / "app" / "static" / "js" / "session_performance.js").is_file()
        ):
            return candidate
    raise SystemExit("Could not locate the WSBCO Golf Coach project root.")


ROOT = find_root()
TEMPLATE = ROOT / "app" / "templates" / "session_detail.html"
JAVASCRIPT = ROOT / "app" / "static" / "js" / "session_performance.js"


def patch_template() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    # Upgrade the earlier shorter label if that patch is already present.
    updated = text.replace(
        "('launch_direction','Start')",
        "('launch_direction','Start Angle')",
    ).replace(
        '("launch_direction", "Start")',
        '("launch_direction", "Start Angle")',
    )

    if "('launch_direction','Start Angle')" not in updated and '("launch_direction", "Start Angle")' not in updated:
        replacements = (
            (
                "('launch_angle','Launch'),('attack_angle','Attack')",
                "('launch_angle','Launch'),('launch_direction','Start Angle'),('attack_angle','Attack')",
            ),
            (
                '("launch_angle", "Launch"), ("attack_angle", "Attack")',
                '("launch_angle", "Launch"), ("launch_direction", "Start Angle"), ("attack_angle", "Attack")',
            ),
        )
        for old, new in replacements:
            if old in updated:
                updated = updated.replace(old, new, 1)
                break
        else:
            raise SystemExit("Could not locate Launch/Attack in session_detail.html; no change was made.")

    TEMPLATE.write_text(updated, encoding="utf-8")


def patch_javascript() -> None:
    text = JAVASCRIPT.read_text(encoding="utf-8")
    if 'launch_direction: "°"' in text or "launch_direction:'°'" in text:
        return
    replacements = (
        (
            '        launch_angle: "°",\n        attack_angle: "°",',
            '        launch_angle: "°",\n        launch_direction: "°",\n        attack_angle: "°",',
        ),
        (
            "launch_angle:'°',attack_angle:'°'",
            "launch_angle:'°',launch_direction:'°',attack_angle:'°'",
        ),
    )
    for old, new in replacements:
        if old in text:
            JAVASCRIPT.write_text(text.replace(old, new, 1), encoding="utf-8")
            return
    raise SystemExit("Could not locate Launch/Attack units in session_performance.js; no change was made.")


def main() -> None:
    patch_template()
    patch_javascript()
    print("Added Start Angle to selected-shot Launch Metrics.")


if __name__ == "__main__":
    main()

