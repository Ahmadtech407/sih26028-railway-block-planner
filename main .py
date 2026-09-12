"""
FastAPI Main Application.
Indian Railways AI Section Controller & Block Planner Backend (SIH26028).
"""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.database import init_database

from backend.routes.sections import router as sections_router
from backend.routes.trains import router as trains_router
from backend.routes.conflicts import router as conflicts_router
from backend.routes.optimizer import router as optimizer_router
from backend.routes.blocks import router as blocks_router
from backend.routes.ai_agent import router as ai_router
from backend.routes.intelligence import router as intelligence_router
from backend.routes.auth import router as auth_router 
from backend.websocket import ws_manager


# -----------------------------------------------------------------------------
# Authentication / persistent user storage
# -----------------------------------------------------------------------------
DB_PATH = os.getenv("RAILTRACK_DB_PATH", os.path.join("data", "railtrack.db"))
JWT_SECRET = os.getenv("RAILTRACK_JWT_SECRET", "change-this-in-production")
JWT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


def init_auth_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                identifier TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()


def normalize_identifier(identifier: str) -> str:
    return identifier.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1
    )
    return base64.urlsafe_b64encode(salt).decode() + ":" + base64.urlsafe_b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, digest_b64 = stored.split(":", 1)
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def create_token(user_id: int) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64url(
        json.dumps(
            {"sub": str(user_id), "exp": int(time.time()) + JWT_TTL_SECONDS},
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{b64url(signature)}"


def decode_token(token: str) -> int:
    try:
        header, payload, signature = token.split(".")
        expected = b64url(
            hmac.new(
                JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256
            ).digest()
        )
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(claims["exp"]) < int(time.time()):
            raise ValueError("expired token")
        return int(claims["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token")


def get_bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer access token required")
    return authorization.split(" ", 1)[1].strip()


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    identifier: str = Field(min_length=3, max_length=150, description="Email or mobile number")
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=1, max_length=128)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    
    print("=" * 70)
    print(" [IR-SIH] Indian Railways AI Section Controller Backend API")
    print("          Swagger Docs: http://localhost:8000/docs")
    print("          ReDoc:        http://localhost:8000/redoc")
    print("          Auth DB:      " + DB_PATH)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sections_router, prefix="/api")
app.include_router(trains_router, prefix="/api")
app.include_router(conflicts_router, prefix="/api")
app.include_router(optimizer_router, prefix="/api")
app.include_router(blocks_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(intelligence_router, prefix="/api")
app.include_router(auth_router, prefix="/api")


@app.post("/api/auth/signup", status_code=201, summary="Create passenger account")
async def signup(request: SignupRequest):
    identifier = normalize_identifier(request.identifier)
    if not identifier:
        raise HTTPException(status_code=400, detail="Email or mobile number is required")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                "INSERT INTO users (name, identifier, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (request.name.strip(), identifier, hash_password(request.password), int(time.time())),
            )
            user_id = cursor.lastrowid
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="An account already exists for this email/mobile number")

    return {
        "message": "Account created successfully",
        "access_token": create_token(user_id),
        "token_type": "bearer",
        "user": {"id": user_id, "name": request.name.strip(), "identifier": identifier},
    }


@app.post("/api/auth/login", summary="Sign in passenger")
async def login(request: LoginRequest):
    identifier = normalize_identifier(request.identifier)
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, name, identifier, password_hash FROM users WHERE identifier = ?",
            (identifier,),
        ).fetchone()

    if not row or not verify_password(request.password, row[3]):
        raise HTTPException(status_code=401, detail="Invalid email/mobile number or password")

    return {
        "message": "Login successful",
        "access_token": create_token(row[0]),
        "token_type": "bearer",
        "user": {"id": row[0], "name": row[1], "identifier": row[2]},
    }


@app.get("/api/auth/me", summary="Get signed-in passenger")
async def me(authorization: Optional[str] = Header(default=None)):

    # Kept explicit so Swagger can still exercise the endpoint; browser clients should
    # send Authorization: Bearer <token>.
    token = get_bearer_token(authorization)
    user_id = decode_token(token)
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, name, identifier, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="User account no longer exists")
    return {"id": row[0], "name": row[1], "identifier": row[2], "created_at": row[3]}


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


@app.websocket("/ws/telemetry")
async def websocket_telemetry_feed(websocket: WebSocket):
    """Real-time WebSocket telemetry stream for live train positions and signals."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"status": "PONG", "received": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
