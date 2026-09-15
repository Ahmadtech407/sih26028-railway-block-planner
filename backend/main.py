"""
FastAPI Main Application.

Indian Railways AI Section Controller & Block Planner Backend (SIH26028).
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.sections import router as sections_router
from backend.routes.trains import router as trains_router
from backend.routes.conflicts import router as conflicts_router
from backend.routes.optimizer import router as optimizer_router
from backend.routes.blocks import router as blocks_router
from backend.routes.ai_agent import router as ai_router
from backend.routes.intelligence import router as intelligence_router
from backend.routes.auth import router as auth_router
from backend.routes.tickets import router as tickets_router
from backend.database import init_database
from backend.websocket import ws_manager

logger = logging.getLogger(__name__)

async def telemetry_broadcast_loop():
    """Continuously push active train telemetry to connected WebSocket clients."""
    from backend.services.train_service import get_trains_for_section
    while True:
        try:
            if ws_manager.active_connections:
                trains = get_trains_for_section("KNP-PRYJ-SEC-B")
                payload = {
                    "type": "TELEMETRY_STREAM",
                    "section_id": "KNP-PRYJ-SEC-B",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "train_count": len(trains),
                    "trains": [t.model_dump() for t in trains],
                }
                await ws_manager.broadcast(payload)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.debug("Telemetry broadcast loop error: %s", exc)
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    telemetry_task = asyncio.create_task(telemetry_broadcast_loop())

    print("=" * 70)
    print("[IR-SIH] Indian Railways AI Section Controller Backend API")
    print("       Swagger Docs: http://localhost:8000/docs")
    print("       ReDoc:        http://localhost:8000/redoc")
    print("=" * 70)

    yield

    telemetry_task.cancel()
    try:
        await telemetry_task
    except asyncio.CancelledError:
        pass
    print("Shutting down Railway Backend...")

app = FastAPI(
    title="Indian Railways AI Section Controller & Block Planner API",
    description=(
        "Production REST & WebSocket API for Problem Statement SIH26028.\n\n"
        "Features:\n"
        "- **Section Management**: Real-time track occupancy and topology.\n"
        "- **Kinematics & Telemetry**: Dead-reckoning position extrapolation.\n"
        "- **Conflict Detection**: Automated scan against train priority hierarchies.\n"
        "- **OR-Tools CP-SAT Optimizer**: Zero-conflict mathematical maintenance allocation.\n"
        "- **AI Section Controller**: Antigravity/Gemini NLP assistant integration.\n"
        "- **Authentication**: Persistent accounts with password hashing and JWT tokens."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# -------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------

_cors_env = os.getenv("CORS_ORIGINS", "*").strip()
if _cors_env == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# API Routers
# -------------------------------------------------------------------

app.include_router(sections_router, prefix="/api")
app.include_router(trains_router, prefix="/api")
app.include_router(conflicts_router, prefix="/api")
app.include_router(optimizer_router, prefix="/api")
app.include_router(blocks_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(intelligence_router, prefix="/api")

# Authentication router
app.include_router(auth_router, prefix="/api")

# Ticket Scanner & PNR Verification router
app.include_router(tickets_router, prefix="/api")


# -------------------------------------------------------------------
# Root Health Check
# -------------------------------------------------------------------

@app.get("/", summary="Root Health Check")
async def root():
    return {
        "system": "Indian Railways AI Section Controller & Block Planner (SIH26028)",
        "status": "ONLINE",
        "version": "1.0.0",
        "docs_url": "/docs",
        "api_prefix": "/api",
        "authentication": "enabled",
    }


@app.get("/health", summary="Deep System & Service Health Check")
async def health():
    """Returns granular operational health status of all internal subsystems."""
    from backend.services.ml_prediction_service import get_model_info
    from backend.services.govt_railway_service import get_feed_status
    from backend.services.weather_service import get_weather_cache_stats

    ml_info = get_model_info()
    feed_status = get_feed_status()
    weather_stats = get_weather_cache_stats()

    subsystems = {
        "api": {"status": "HEALTHY", "uptime": "ONLINE"},
        "ml_inference": {
            "status": "HEALTHY" if ml_info.get("status") == "LOADED" else "DEGRADED",
            "model_version": ml_info.get("model_version"),
            "framework": ml_info.get("framework"),
        },
        "railway_feed": {
            "status": "CONNECTED" if feed_status.get("configured") else "OFFLINE_CALIBRATED",
            "provider": feed_status.get("provider"),
            "data_mode": feed_status.get("data_mode"),
        },
        "weather_cache": weather_stats,
        "websocket": {
            "active_subscribers": len(ws_manager.active_connections),
            "status": "OPERATIONAL",
        },
    }

    overall_healthy = (
        subsystems["api"]["status"] == "HEALTHY"
        and subsystems["websocket"]["status"] == "OPERATIONAL"
    )

    return {
        "status": "HEALTHY" if overall_healthy else "DEGRADED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subsystems": subsystems,
    }


# -------------------------------------------------------------------
# WebSocket Telemetry
# -------------------------------------------------------------------

@app.websocket("/ws/telemetry")
async def websocket_telemetry_feed(websocket: WebSocket):
    """
    Real-time WebSocket telemetry stream for live train positions and signals.
    """

    await ws_manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()

            await websocket.send_json(
                {
                    "status": "PONG",
                    "received": data,
                }
            )

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
