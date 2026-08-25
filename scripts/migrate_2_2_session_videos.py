from app.database import Base, DATABASE_PATH, engine
import app.models  # noqa: F401

def main():
    Base.metadata.create_all(bind=engine)
    print(f"Phase 2.2 tables ready: {DATABASE_PATH}")

if __name__ == "__main__":
    main()
