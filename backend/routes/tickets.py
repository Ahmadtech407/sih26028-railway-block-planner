"""
FastAPI Routes for Ticket Scanning & Verification (SIH26028).

Provides endpoints for mobile and web passenger apps to verify QR codes,
barcodes, PNR numbers, electronic reservation slips against live manifests,
and securely associate saved journeys with authenticated passengers.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from backend.services.ticket_service import verify_ticket, sanitize_payload
from backend.routes.auth import bearer_scheme, decode_token
from backend.database import save_user_journey, get_user_journey, clear_user_journey


router = APIRouter(prefix="/tickets", tags=["Tickets & PNR Verification"])


class TicketVerifyRequest(BaseModel):
    payload: str = Field(..., description="Scanned QR code content, barcode string, or 10-digit PNR number")


class TicketVerifyResponse(BaseModel):
    status: str
    match_verified: bool
    pnr: Optional[str] = None
    ticket_id: Optional[str] = None
    passenger: Optional[Dict[str, Any]] = None
    journey: Optional[Dict[str, Any]] = None
    booking: Optional[Dict[str, Any]] = None
    verified_at: Optional[str] = None
    security_hash: Optional[str] = None
    message: Optional[str] = None


class SaveJourneyRequest(BaseModel):
    pnr: str = Field(..., description="10-digit IRCTC PNR number or ticket ID")
    ticket_data: Optional[Dict[str, Any]] = Field(None, description="Verified ticket object (optional, will be verified if omitted)")


# -------------------------------------------------------------------
# Authenticated Journey Endpoints (Declared before dynamic path parameter /{pnr_or_id})
# -------------------------------------------------------------------

@router.post("/save-journey", summary="Save verified journey to passenger account")
async def save_passenger_journey(
    req: SaveJourneyRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """
    Associate a verified PNR or ticket payload with the currently authenticated passenger.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication token required to save journey")
    user_id = decode_token(credentials.credentials)

    ticket = req.ticket_data
    if not ticket or not ticket.get("match_verified"):
        ticket = verify_ticket(req.pnr)

    if not ticket.get("match_verified"):
        raise HTTPException(status_code=400, detail="Cannot save unverified or invalid ticket")

    pnr = ticket.get("pnr") or req.pnr
    ok = save_user_journey(user_id=user_id, pnr=pnr, ticket_data=ticket)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save journey to database")

    return {
        "status": "SUCCESS",
        "message": f"Journey for PNR {pnr} successfully associated with your account.",
        "pnr": pnr,
        "journey": ticket.get("journey"),
        "booking": ticket.get("booking"),
        "saved_ticket": ticket,
    }


@router.get("/my-journey", summary="Get authenticated passenger's saved journey")
async def get_my_journey(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """
    Retrieve previously saved journey for the authenticated passenger.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication token required")
    user_id = decode_token(credentials.credentials)
    journey = get_user_journey(user_id)
    if not journey:
        return {"has_journey": False, "journey": None, "message": "No active journey saved for this account."}
    return {
        "has_journey": True,
        "journey": journey,
        "pnr": journey.get("pnr"),
    }


@router.delete("/my-journey", summary="Disassociate saved journey from passenger account")
async def clear_my_journey(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """
    Remove the currently saved journey from the passenger account.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication token required")
    user_id = decode_token(credentials.credentials)
    ok = clear_user_journey(user_id)
    return {"status": "SUCCESS", "message": "Saved journey cleared."}


# -------------------------------------------------------------------
# Ticket Verification Endpoints
# -------------------------------------------------------------------

@router.get("/{pnr_or_id}", summary="Lookup ticket by PNR or Ticket ID")
async def get_ticket_details(pnr_or_id: str):
    """
    Retrieve confirmed passenger and journey information for a PNR or Ticket ID.
    """
    result = verify_ticket(pnr_or_id)
    if not result.get("match_verified"):
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "PNR not found. Please check the PNR and try again.",
                "detail": "PNR not found. Please check the PNR and try again.",
            },
        )
    res = result.copy()
    res["success"] = True
    return res


@router.post("/verify", summary="Verify scanned QR/Barcode payload")
async def verify_scanned_ticket(req: TicketVerifyRequest):
    """
    Verify a scanned payload (e.g. from camera QR scanner, barcode reader, or manual input)
    and return verified passenger, coach, seat, and journey data.
    """
    result = verify_ticket(req.payload)
    if not result.get("match_verified"):
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "PNR not found. Please check the PNR and try again.",
                "detail": "PNR not found. Please check the PNR and try again.",
            },
        )
    res = result.copy()
    res["success"] = True
    return res


@router.post("/scan-image", response_model=TicketVerifyResponse, summary="Decode QR code from uploaded image")
async def scan_ticket_image(file: UploadFile = File(...)):
    """
    Accept an uploaded ticket snapshot/photo and decode any visible QR code or barcode using OpenCV.
    """
    try:
        import numpy as np
        import cv2

        contents = await file.read()
        np_arr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Unable to decode image data")

        detector = cv2.QRCodeDetector()
        val, points, _ = detector.detectAndDecode(img)
        if not val:
            # Try grayscale and threshold
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            val, points, _ = detector.detectAndDecode(gray)

        if not val:
            return {
                "status": "UNREADABLE",
                "match_verified": False,
                "message": "No clear QR code or barcode was detected in the captured image. Please try again with better lighting or enter the PNR manually.",
            }

        return verify_ticket(val)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image scanning failed: {str(e)}")
