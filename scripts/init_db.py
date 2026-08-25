"""
Initialize the WSBCO Golf Coach SQLite database.
"""

from app.database import Base, DATABASE_PATH, engine
import app.models  # noqa: F401


def main():
    Base.metadata.create_all(bind=engine)
    print(f"Database ready: {DATABASE_PATH}")


if __name__ == "__main__":
    main()
