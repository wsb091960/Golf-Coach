from __future__ import annotations

from sqlalchemy import inspect, text
from app.database import DATABASE_PATH, engine


def main() -> None:
    inspector = inspect(engine)

    if "students" not in inspector.get_table_names():
        raise SystemExit("The students table does not exist. Run Phase 2.1 first.")

    columns = {column["name"] for column in inspector.get_columns("students")}

    if "handedness" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE students "
                    "ADD COLUMN handedness VARCHAR(20) DEFAULT 'Unknown'"
                )
            )
        print("Added students.handedness")
    else:
        print("students.handedness already exists")

    print(f"Database updated: {DATABASE_PATH}")


if __name__ == "__main__":
    main()
