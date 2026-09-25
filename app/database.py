"""
WSBCO Golf Coach
SQLite / SQLAlchemy database configuration.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker


APP_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = APP_DIR / "data"
DATA_DIR = Path(
    os.getenv("WSBCO_DATA_DIR", str(DEFAULT_DATA_DIR))
).expanduser()

# Production can now point SQLite at a Render persistent disk:
# DATABASE_URL=sqlite:////var/data/golf_coach.db
# Local development keeps using app/data/golf_coach.db by default.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH: Path | None = DATA_DIR / "golf_coach.db"
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
else:
    database_config = make_url(DATABASE_URL)
    database_name = database_config.database
    DATABASE_PATH = None

    if (
        database_config.get_backend_name() == "sqlite"
        and database_name
        and database_name != ":memory:"
    ):
        DATABASE_PATH = Path(database_name).expanduser()
        if not DATABASE_PATH.is_absolute():
            DATABASE_PATH = Path.cwd() / DATABASE_PATH
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

engine_options = {"pool_pre_ping": True}
if make_url(DATABASE_URL).get_backend_name() == "sqlite":
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
