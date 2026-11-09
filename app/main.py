from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers.coach_assistant import router as coach_assistant_router

from app.database import Base, engine
from app.gcie import models as gcie_models
from app.gcie import generated_models as gcie_generated_models
from app.gcie.router import router as gcie_router
from app.routers.gapping import router as gapping_router
from app.routers.analysis import router as analysis_router
from app.routers.dashboard import router as dashboard_router
from app.routers.public_home import router as public_home_router
from app.routers.auth import router as auth_router, GolfOwnerAuthMiddleware
from app.routers.importer import router as importer_router
from app.routers.sessions import router as sessions_router
from app.routers.ball_flight_simulator import router as ball_flight_simulator_router
from app.routers.students import router as students_router
from app.routers.videos import router as videos_router
from app.routers.biomechanics import router as biomechanics_router
from app.routers.swing_contact_sheet import router as swing_contact_sheet_router
from app.routers import crm_sync as crm_sync_router
from app.mcp.simulator_server import mcp as simulator_mcp, http_app as simulator_mcp_http_app

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Mounted MCP applications do not start their own lifespan, so the host
    # must own the SDK session manager explicitly.
    async with simulator_mcp.session_manager.run():
        yield


app = FastAPI(
    title="WSBCO Golf Coach",
    version="5.3A",
    lifespan=lifespan,
)

app.add_middleware(GolfOwnerAuthMiddleware)

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)

app.include_router(auth_router)
app.include_router(public_home_router)
app.include_router(dashboard_router)
app.include_router(coach_assistant_router)
app.include_router(students_router)
app.include_router(sessions_router)
app.include_router(gcie_router)
app.include_router(ball_flight_simulator_router)
app.include_router(importer_router)
app.include_router(analysis_router)
app.include_router(videos_router)
app.include_router(biomechanics_router)
app.include_router(swing_contact_sheet_router)
app.include_router(gapping_router)

@app.get("/health", name="health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": "WSBCO Golf Coach",
        "version": app.version,
        "database": "sqlite",
    }

# Register the static workspace routes before the legacy /{analysis_id} route,
# so paths such as /swing-analysis/new are not treated as analysis IDs.
from app.routers import swing_analysis_workspace as swing_analysis_workspace_router
app.include_router(swing_analysis_workspace_router.router)

from app.routers import swing_analysis as swing_analysis_router
app.include_router(swing_analysis_router.router)

from app.routers import swing_analysis_launch as swing_analysis_launch_router
app.include_router(swing_analysis_launch_router.router)

from app.routers import swing_analysis_assist as swing_analysis_assist_router
app.include_router(swing_analysis_assist_router.router)

app.include_router(crm_sync_router.router)

# Stateless, metric-only MCP endpoint used by the standalone simulator.
# It has no connection to the student/session or CRM data workflows.
app.mount("/mcp", simulator_mcp_http_app, name="simulator_mcp")
