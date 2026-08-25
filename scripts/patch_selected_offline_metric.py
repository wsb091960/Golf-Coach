from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "app" / "static" / "js" / "session_performance.js"

OLD = '''        document.querySelectorAll("[data-metric]").forEach(node => {
            const key = node.dataset.metric;
            const value = finite(shot ? shot[key] : null);

            if (value === null) {'''

NEW = '''        document.querySelectorAll("[data-metric]").forEach(node => {
            const key = node.dataset.metric;
            let value = finite(shot ? shot[key] : null);

            // Keep the Offline card consistent with the top-down trajectory.
            // Prefer Garmin's measured value; otherwise use the same calculated
            // landing value already displayed by finalOffline().
            if (
                value === null &&
                key === "offline_distance" &&
                shot
            ) {
                const carry = finite(shot.carry_distance) || 0;
                value = finalOffline(shot, carry);
            }

            if (value === null) {'''


def main() -> None:
    if not JS_PATH.exists():
        raise SystemExit(f"Session performance JavaScript not found: {JS_PATH}")

    text = JS_PATH.read_text(encoding="utf-8")
    if "Keep the Offline card consistent" in text:
        print("Selected-shot Offline metric fix is already installed.")
        return
    if OLD not in text:
        raise SystemExit(
            "Could not locate updateMetrics() in the expected format. "
            "No file was changed."
        )

    JS_PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("Selected-shot Offline now uses measured-first trajectory logic.")


if __name__ == "__main__":
    main()

