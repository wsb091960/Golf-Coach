from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers.gapping import router as gapping_router
from app.routers.analysis import router as analysis_router
from app.routers.dashboard import router as dashboard_router
from app.routers.importer import router as importer_router
from app.routers.sessions import router as sessions_router
from app.routers.students import router as students_router
from app.routers.videos import router as videos_router
from app.routers.biomechanics import router as biomechanics_router

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WSBCO Golf Coach",
    version="2.1.2",
)

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)

app.include_router(dashboard_router)
app.include_router(students_router)
app.include_router(sessions_router)
app.include_router(importer_router)
app.include_router(analysis_router)
app.include_router(videos_router)
app.include_router(biomechanics_router)
app.include_router(gapping_router)

@app.get("/health", name="health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": "WSBCO Golf Coach",
        "version": app.version,
        "database": "sqlite",
    }
