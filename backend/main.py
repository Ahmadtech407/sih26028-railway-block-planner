"""
FastAPI Main Application.

Indian Railways AI Section Controller & Block Planner Backend (SIH26028).
"""

import asyncio
import os
from contextlib import asynccontextmanager

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()

    print("=" * 70)
    print("[IR-SIH] Indian Railways AI Section Controller Backend API")
    print("       Swagger Docs: http://localhost:8000/docs")
    print("       ReDoc:        http://localhost:8000/redoc")
    print("=" * 70)

    yield

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
