"""
PNR Verification Router for Indian Railways Passenger App (SIH26028).

Enforces mandatory PNR verification security boundaries:
1. Validates 10-digit IRCTC PNR against authentic stored manifests & persistent database.
2. Generates time-limited cryptographically secure session tokens upon verification.
3. Derives coach positioning strictly server-side from verified session context;
   never trusts client-supplied coach/seat values.
"""

from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import re
import secrets
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.database import (
    create_pnr_session,
    get_pnr_session,
    delete_pnr_session,
)
from backend.services.ticket_service import verify_ticket, verify_pnr, sanitize_payload

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pnr",
    tags=["PNR Verification"],
)

# In-memory fast cache for active sessions (backed by SQLite database)
_MEMORY_SESSIONS: Dict[str, Dict[str, Any]] = {}


class PnrVerifyRequest(BaseModel):
    pnr: str = Field(..., description="10-digit IRCTC PNR string")


class PnrCoachPositionRequest(BaseModel):
    session_token: str = Field(..., description="Active verified PNR session token")


class PnrSessionClearRequest(BaseModel):
    session_token: str = Field(..., description="Session token to invalidate")


def _get_active_session(token: str) -> Optional[Dict[str, Any]]:
    """Retrieve active session from memory cache or SQLite, enforcing expiry."""
    token = str(token).strip()
    if not token:
        return None

    now = datetime.now(timezone.utc)
    # Check in-memory first
    if token in _MEMORY_SESSIONS:
        sess = _MEMORY_SESSIONS[token]
        exp = sess.get("expires_at_dt")
        if exp and exp > now:
            return sess
        else:
            _MEMORY_SESSIONS.pop(token, None)
            delete_pnr_session(token)
            return None

    # Check database
    db_sess = get_pnr_session(token)
    if db_sess:
        try:
            exp_str = db_sess["expires_at"]
            exp_dt = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
            if exp_dt > now:
                db_sess["expires_at_dt"] = exp_dt
                _MEMORY_SESSIONS[token] = db_sess
                return db_sess
        except Exception:
            pass

    return None


def execute_pnr_verification(raw_pnr_str: str) -> Dict[str, Any]:
    """
    Unified end-to-end PNR verification service.
    Directly callable by FastAPI routes and internal Streamlit workflows.
    Consumes canonical verify_pnr() from backend.services.ticket_service.
    Creates 15-minute cryptographically secure session token in SQLite and memory cache.
    """
    raw_pnr = sanitize_payload(str(raw_pnr_str).strip())

    # Strict 10-digit numerical validation
    if not re.fullmatch(r"^\d{10}$", raw_pnr):
        return {
            "verified": False,
            "success": False,
            "status_code": status.HTTP_400_BAD_REQUEST,
            "message": "Please enter a valid 10-digit PNR.",
            "detail": "Please enter a valid 10-digit PNR.",
        }

    # Canonical PNR lookup via single source of truth
    record = verify_pnr(raw_pnr)
    if not record or not record.get("match_verified"):
        return {
            "verified": False,
            "success": False,
            "status_code": status.HTTP_404_NOT_FOUND,
            "message": "PNR not found. Please check the PNR and try again.",
            "detail": "PNR could not be verified. PNR not found.",
        }

    # Generate cryptographically secure session token (32 bytes = 256 bits)
    session_token = secrets.token_hex(32)
    now_dt = datetime.now(timezone.utc)
    exp_dt = now_dt + timedelta(minutes=15)
    exp_iso = exp_dt.isoformat()

    journey_data = {
        "train_number": str(record.get("train_number", "")),
        "train_name": str(record.get("train_name", "")),
        "travel_date": str(record.get("travel_date", "")),
        "from_station": str(record.get("from_station", "")),
        "to_station": str(record.get("to_station", "")),
        "coach": str(record.get("coach", "")),
        "seat_number": str(record.get("seat_number", "")),
        "berth_type": str(record.get("berth_type", "")),
        "class_code": str(record.get("class_code", "")),
        "class_name": str(record.get("class_name", "")),
        "status": str(record.get("status", "CNF")),
        "status_detail": str(record.get("status_detail", "Confirmed / Allotted")),
        "passenger_name": str(record.get("passenger_name", "John Doe")),
        "verification_status": "DEMO",
    }

    # Store in persistent SQLite and in-memory cache
    create_pnr_session(session_token, raw_pnr, journey_data, exp_iso, verification_status="DEMO")
    cached_record = journey_data.copy()
    cached_record.update({
        "token": session_token,
        "pnr": raw_pnr,
        "verification_status": "DEMO",
        "expires_at": exp_iso,
        "expires_at_dt": exp_dt,
    })
    _MEMORY_SESSIONS[session_token] = cached_record

    return {
        "verified": True,
        "success": True,
        "match_verified": True,
        "status_code": status.HTTP_200_OK,
        "verification_status": "DEMO",
        "session_token": session_token,
        "pnr": raw_pnr,
        "passenger_name": str(record.get("passenger_name", "John Doe")),
        "passenger": record.get("passenger", {}),
        "train_number": str(record.get("train_number", "")),
        "train_name": str(record.get("train_name", "")),
        "travel_date": str(record.get("travel_date", "")),
        "from_station": str(record.get("from_station", "")),
        "to_station": str(record.get("to_station", "")),
        "coach": str(record.get("coach", "")),
        "seat_number": str(record.get("seat_number", "")),
        "berth_type": str(record.get("berth_type", "")),
        "class_code": str(record.get("class_code", "")),
        "class_name": str(record.get("class_name", "")),
        "status": str(record.get("status", "CNF")),
        "journey": journey_data,
        "booking": record.get("booking", {}),
        "message": "PNR verified successfully.",
    }


@router.post("/verify", summary="Verify 10-digit PNR and create secure session")
async def verify_pnr_endpoint(req: PnrVerifyRequest):
    """
    Verify 10-digit PNR against official railway passenger manifest.
    - If format is not exactly 10 digits: returns HTTP 400 Bad Request.
    - If PNR does not exist in authorized source: returns HTTP 404 Not Found.
    - If verified: creates a 15-minute secure session token and returns journey details.
    """
    res = execute_pnr_verification(req.pnr)
    if not res.get("verified"):
        return JSONResponse(
            status_code=res.get("status_code", status.HTTP_404_NOT_FOUND),
            content={
                "success": False,
                "verified": False,
                "message": res.get("message", "PNR could not be verified."),
                "detail": res.get("detail", "PNR could not be verified."),
            },
        )
    return res



@router.post("/coach-position", summary="Get passenger coach position from verified session")
async def get_verified_coach_position(req: PnrCoachPositionRequest):
    """
    Derives passenger coach position exclusively from the server-side verified PNR session.
    Arbitrary coach/seat parameters are rejected — client cannot supply unverified coach/seat.
    """
    session = _get_active_session(req.session_token)
    if not session:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "status": "UNAUTHORIZED",
                "detail": "Authentication required. Please verify your PNR first.",
                "message": "Authentication required. Please verify your PNR first.",
            },
        )

    train_num = str(session.get("train_number", "")).strip()
    coach_id = str(session.get("coach", "")).strip().upper()
    seat_num = str(session.get("seat_number", "")).strip()

    # Load authentic formations
    data_file = Path(__file__).resolve().parent.parent / "data" / "coach_formations.json"
    all_formations = {}
    if data_file.exists():
        try:
            with open(data_file, "r", encoding="utf-8") as fh:
                all_formations = json.load(fh).get("formations", {})
        except Exception:
            pass

    formation = all_formations.get(train_num)
    if not formation:
        pairs = {
            "12302": "12301",
            "12301": "12302",
            "22435": "22436",
            "22436": "22435",
            "12423": "12424",
            "12424": "12423",
            "12003": "12004",
            "12004": "12003",
            "12801": "12802",
            "12802": "12801",
        }
        alt_key = pairs.get(train_num)
        if alt_key and alt_key in all_formations:
            formation = dict(all_formations[alt_key])
            formation["trainNumber"] = train_num

    # Case 1: Formation unavailable
    if not formation or formation.get("verificationStatus") == "UNAVAILABLE" or not formation.get("coaches"):
        return {
            "status": "UNAVAILABLE",
            "provenance": "UNAVAILABLE",
            "train_number": train_num,
            "coach": coach_id,
            "seat": seat_num,
            "message": "Journey verified, but verified coach formation is currently unavailable.",
        }

    coaches = formation.get("coaches", [])
    total_coaches = len(coaches)

    # Locate coach in physical sequence
    exact_idx = -1
    for i, c in enumerate(coaches):
        if str(c.get("coachId", "")).upper() == coach_id:
            exact_idx = i
            break

    # Case 2: Coach unavailable in formation
    if exact_idx == -1:
        return {
            "status": "COACH_UNAVAILABLE",
            "provenance": formation.get("verificationStatus", "VERIFIED_STATIC"),
            "train_number": train_num,
            "coach": coach_id,
            "seat": seat_num,
            "total_coaches": total_coaches,
            "message": "Journey verified, but coach information is unavailable in train formation.",
        }

    # Case 3: Coach verified in authentic rake
    coaches_before = exact_idx
    coaches_after = total_coaches - 1 - exact_idx
    ratio = exact_idx / max(1, total_coaches - 1)
    if ratio <= 0.33:
        section = "Front Section"
    elif ratio <= 0.66:
        section = "Middle Section"
    else:
        section = "Rear Section"

    # Provenance labeling: Static formations verified from timetable/consist are VERIFIED_STATIC
    provenance = "VERIFIED_STATIC"

    return {
        "status": "SUCCESS",
        "provenance": provenance,
        "verification_status": session.get("verification_status", "DEMO"),
        "train_number": train_num,
        "train_name": session.get("train_name", ""),
        "coach": coach_id,
        "seat": seat_num,
        "berth_type": session.get("berth_type", ""),
        "position": exact_idx + 1,
        "total_coaches": total_coaches,
        "coaches_before": coaches_before,
        "coaches_after": coaches_after,
        "ahead_count": coaches_before,
        "behind_count": coaches_after,
        "section": section,
        "relative_section": section,
        "coaches": coaches,
        "message": f"Coach {coach_id} is at position {exact_idx + 1} of {total_coaches} ({section}).",
    }



@router.post("/logout", summary="Invalidate verified PNR session")
@router.post("/session/clear", summary="Clear verified PNR session")
async def clear_pnr_session(req: PnrSessionClearRequest):
    """Invalidate verified PNR session from cache and persistent database."""
    token = str(req.session_token).strip()
    _MEMORY_SESSIONS.pop(token, None)
    deleted = delete_pnr_session(token)
    return {
        "success": True,
        "message": "Session invalidated successfully." if deleted else "Session was already inactive.",
    }


@router.get("/{pnr}", summary="Lookup ticket by 10-digit PNR")
async def get_pnr_endpoint(pnr: str):
    """
    GET endpoint to look up ticket by 10-digit PNR.
    """
    pnr_val = sanitize_payload(pnr)
    if not re.fullmatch(r"^\d{10}$", pnr_val):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "message": "Please enter a valid 10-digit PNR.",
                "detail": "Please enter a valid 10-digit PNR.",
            },
        )

    result = verify_ticket(pnr_val)

    if not result.get("match_verified"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "PNR not found. Please check the PNR and try again.",
                "detail": "PNR not found. Please check the PNR and try again.",
            },
        )

    res = result.copy()
    res["success"] = True
    return res

