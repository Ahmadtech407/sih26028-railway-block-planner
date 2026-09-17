"""
PNR Verification Router for Indian Railways Passenger App (SIH26028).

Validates 10-digit IRCTC PNR against stored manifests and persistent database.
Returns official passenger details if valid, or HTTP 404 if not found.
"""

from typing import Any, Dict
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.services.ticket_service import verify_ticket, sanitize_payload


router = APIRouter(
    prefix="/pnr",
    tags=["PNR Verification"],
)


class PnrVerifyRequest(BaseModel):
    pnr: str = Field(..., description="10-digit IRCTC PNR string", example="8429103847")


@router.post("/verify", summary="Verify 10-digit PNR")
async def verify_pnr_endpoint(req: PnrVerifyRequest):
    """
    Verify 10-digit PNR against railway passenger manifest.
    If PNR exists: returns confirmed ticket, coach, seat, and journey information.
    If PNR does not exist: returns HTTP 404 with clean not-found message.
    """
    pnr_val = sanitize_payload(req.pnr)
    result = verify_ticket(pnr_val)

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


@router.get("/{pnr}", summary="Lookup ticket by 10-digit PNR")
async def get_pnr_endpoint(pnr: str):
    """
    GET endpoint to look up ticket by 10-digit PNR.
    """
    pnr_val = sanitize_payload(pnr)
    result = verify_ticket(pnr_val)

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
