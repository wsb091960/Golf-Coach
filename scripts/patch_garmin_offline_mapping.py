from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORTER = ROOT / "app" / "routers" / "importer.py"

OLD = '"offline_distance": ["offlinedistance", "offline", "lateraldistance"],'
NEW = (
    '"offline_distance": ['
    '"carrydeviationdistance", '
    '"offlinedistance", '
    '"offline", '
    '"lateraldistance", '
    '"carrydeviation"'
    '],'
)


def main() -> None:
    if not IMPORTER.exists():
        raise SystemExit(f"Importer not found: {IMPORTER}")

    text = IMPORTER.read_text(encoding="utf-8")

    if "carrydeviationdistance" in text:
        print("Garmin offline mapping is already installed.")
        return

    if OLD not in text:
        raise SystemExit(
            "Could not locate the expected offline_distance alias list. "
            "No files were changed."
        )

    IMPORTER.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("Mapped Garmin Carry Deviation Distance to offline_distance.")


if __name__ == "__main__":
    main()

