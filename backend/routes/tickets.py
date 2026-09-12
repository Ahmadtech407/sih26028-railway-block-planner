"""
FastAPI Routes for Ticket Scanning & Verification (SIH26028).

Provides endpoints for mobile and web passenger apps to verify QR codes,
barcodes, PNR numbers, and electronic reservation slips against live manifests.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field

from backend.services.ticket_service import verify_ticket, sanitize_payload


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


@router.get("/{pnr_or_id}", response_model=TicketVerifyResponse, summary="Lookup ticket by PNR or Ticket ID")
async def get_ticket_details(pnr_or_id: str):
    """
    Retrieve confirmed passenger and journey information for a PNR or Ticket ID.
    """
    result = verify_ticket(pnr_or_id)
    if not result.get("match_verified") and result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("message", "Invalid ticket identifier"))
    return result


@router.post("/verify", response_model=TicketVerifyResponse, summary="Verify scanned QR/Barcode payload")
async def verify_scanned_ticket(req: TicketVerifyRequest):
    """
    Verify a scanned payload (e.g. from camera QR scanner, barcode reader, or manual input)
    and return verified passenger, coach, seat, and journey data.
    """
    result = verify_ticket(req.payload)
    return result


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
