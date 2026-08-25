from __future__ import annotations
from sqlalchemy import inspect, text
from app.database import DATABASE_PATH, engine

def main() -> None:
    inspector = inspect(engine)
    if "shots" not in inspector.get_table_names():
        raise SystemExit("The shots table does not exist. Run Phase 2.1 first.")
    columns = {c["name"] for c in inspector.get_columns("shots")}
    if "shot_shape" not in columns:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE shots ADD COLUMN shot_shape VARCHAR(50) DEFAULT ''"
            ))
        print("Added shots.shot_shape")
    else:
        print("shots.shot_shape already exists")
    print(f"Database updated: {DATABASE_PATH}")

if __name__ == "__main__":
    main()
