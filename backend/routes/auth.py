import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import BaseModel, Field

from backend.database import (
    create_user,
    get_user_by_identifier,
    get_user_by_id,
    get_user_journey,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

# Swagger/OpenAPI Bearer authentication
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

_is_prod = (
    os.getenv("ENVIRONMENT", "").lower() == "production"
    or os.getenv("RENDER", "").lower() in ("true", "1")
)
_env_secret = os.getenv("RAILTRACK_JWT_SECRET") or os.getenv("JWT_SECRET_KEY")

if _is_prod:
    if not _env_secret or _env_secret in ("change-this-in-production", "replace_me"):
        raise RuntimeError(
            "CRITICAL PRODUCTION SECURITY ERROR: RAILTRACK_JWT_SECRET or JWT_SECRET_KEY "
            "must be explicitly set in production environment to prevent session invalidation."
        )
    JWT_SECRET = _env_secret
else:
    # Deterministic development secret — avoids token forgery & survives restart across workers
    JWT_SECRET = _env_secret or "railtrack-dev-insecure-persistent-secret-key-32bytes" 

JWT_TTL_SECONDS = 60 * 60 * 24 * 7
# 7 days


# ---------------------------------------------------------
# Password handling
# ---------------------------------------------------------

def hash_password(password: str) -> str:
    """Create a salted scrypt password hash."""

    salt = secrets.token_bytes(16)

    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )

    return (
        base64.urlsafe_b64encode(salt)
        .rstrip(b"=")
        .decode("ascii")
        + ":"
        + base64.urlsafe_b64encode(digest)
        .rstrip(b"=")
        .decode("ascii")
    )


def verify_password(
    password: str,
    stored: str,
) -> bool:
    """Verify a password against its stored scrypt hash."""

    try:
        salt_b64, digest_b64 = stored.split(
            ":",
            1,
        )

        salt = base64.urlsafe_b64decode(
            salt_b64.encode()
            + b"=" * (-len(salt_b64) % 4)
        )

        expected = base64.urlsafe_b64decode(
            digest_b64.encode()
            + b"=" * (-len(digest_b64) % 4)
        )

        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
        )

        return hmac.compare_digest(
            actual,
            expected,
        )

    except (
        ValueError,
        TypeError,
    ):
        return False


# ---------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------

def b64url(data: bytes) -> str:
    """Encode bytes using URL-safe base64 without padding."""

    return (
        base64.urlsafe_b64encode(data)
        .rstrip(b"=")
        .decode("ascii")
    )


def create_token(user_id: int, role: str = "VIEWER") -> str:
    """Create an access token for a user with role claim."""

    header = b64url(
        json.dumps(
            {
                "alg": "HS256",
                "typ": "JWT",
            },
            separators=(",", ":"),
        ).encode()
    )

    payload = b64url(
        json.dumps(
            {
                "sub": str(user_id),
                "role": role,
                "exp": int(time.time())
                + JWT_TTL_SECONDS,
            },
            separators=(",", ":"),
        ).encode()
    )

    signing_input = (
        f"{header}.{payload}"
    ).encode()

    signature = hmac.new(
        JWT_SECRET.encode(),
        signing_input,
        hashlib.sha256,
    ).digest()

    return (
        f"{header}.{payload}.{b64url(signature)}"
    )


def decode_token(token: str) -> int:
    """Validate an access token and return the user ID."""

    try:
        header, payload, signature = token.split(
            ".",
            2,
        )

        expected = b64url(
            hmac.new(
                JWT_SECRET.encode(),
                f"{header}.{payload}".encode(),
                hashlib.sha256,
            ).digest()
        )

        if not hmac.compare_digest(
            signature,
            expected,
        ):
            raise ValueError(
                "invalid signature"
            )

        claims = json.loads(
            base64.urlsafe_b64decode(
                payload
                + "=" * (-len(payload) % 4)
            )
        )

        if int(claims["exp"]) < int(time.time()):
            raise ValueError(
                "expired token"
            )

        return int(claims["sub"])

    except (
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        )


def decode_token_claims(token: str) -> dict:
    """Validate an access token and return all claims including role."""
    try:
        header, payload, signature = token.split(".", 2)
        expected = b64url(
            hmac.new(
                JWT_SECRET.encode(),
                f"{header}.{payload}".encode(),
                hashlib.sha256,
            ).digest()
        )
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        claims = json.loads(
            base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        )
        if int(claims["exp"]) < int(time.time()):
            raise ValueError("expired token")
        return {
            "user_id": int(claims["sub"]),
            "role": claims.get("role", "VIEWER"),
            "exp": claims["exp"],
        }
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        )


# ---------------------------------------------------------
# Request models
# ---------------------------------------------------------

class SignupRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    identifier: str = Field(
        min_length=3,
        max_length=150,
        description="Email or mobile number",
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    role: Optional[str] = Field(
        "VIEWER",
        description="Role: VIEWER, SECTION_CONTROLLER, OPERATIONS, ENGINEERING_PWAY, TRACTION_OHE, ADMIN",
    )


class LoginRequest(BaseModel):
    identifier: str = Field(
        min_length=3,
        max_length=150,
    )

    password: str = Field(
        min_length=1,
        max_length=128,
    )


# ---------------------------------------------------------
# SIGNUP
# ---------------------------------------------------------

@router.post(
    "/signup",
    status_code=201,
    summary="Create passenger account",
)
async def signup(
    request: SignupRequest,
):
    """Create a passenger account."""

    name = request.name.strip()

    identifier = request.identifier.strip().lower()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name is required",
        )

    if not identifier:
        raise HTTPException(
            status_code=400,
            detail="Email or mobile number is required",
        )

    try:
        password_hash = hash_password(
            request.password
        )

        role = (request.role or "VIEWER").upper()
        user_id = create_user(
            name=name,
            identifier=identifier,
            password_hash=password_hash,
            created_at=int(time.time()),
            role=role,
        )

    except Exception as exc:
        error_message = str(exc).lower()

        if (
            "duplicate" in error_message
            or "unique" in error_message
            or "23505" in error_message
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "An account already exists for "
                    "this email/mobile number"
                ),
            )

        raise HTTPException(
            status_code=500,
            detail="Could not create passenger account",
        )

    return {
        "message": "Account created successfully",
        "access_token": create_token(user_id, role=role),
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": name,
            "identifier": identifier,
        },
    }


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

@router.post(
    "/login",
    summary="Sign in passenger",
)
async def login(
    request: LoginRequest,
):
    """Authenticate a passenger."""

    identifier = (
        request.identifier
        .strip()
        .lower()
    )

    row = get_user_by_identifier(
        identifier
    )

    if not row:
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid email/mobile number "
                "or password"
            ),
        )

    if not verify_password(
        request.password,
        row["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid email/mobile number "
                "or password"
            ),
        )

    return {
        "message": "Login successful",
        "access_token": create_token(
            row["id"],
            role=row.get("role", "VIEWER"),
        ),
        "token_type": "bearer",
        "user": {
            "id": row["id"],
            "name": row["name"],
            "identifier": row["identifier"],
            "active_journey": get_user_journey(row["id"]),
        },
    }


# ---------------------------------------------------------
# CURRENT USER
# ---------------------------------------------------------

@router.get(
    "/me",
    summary="Get signed-in passenger",
)
async def me(
    credentials: Optional[
        HTTPAuthorizationCredentials
    ] = Depends(
        bearer_scheme
    ),
):
    """Return the currently authenticated passenger."""

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Bearer access token required",
        )

    token = credentials.credentials

    user_id = decode_token(token)

    row = get_user_by_id(
        user_id
    )

    if not row:
        raise HTTPException(
            status_code=401,
            detail="User account no longer exists",
        )

    return {
        "id": row["id"],
        "name": row["name"],
        "identifier": row["identifier"],
        "role": row.get("role", "VIEWER"),
        "created_at": row["created_at"],
        "active_journey": get_user_journey(user_id),
    }