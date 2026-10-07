"""
Clearance and Multi-Department Review API Routes.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Provides endpoints to manage the human-in-the-loop clearance lifecycle.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.schemas.clearance_models import (
    ClearanceAdvanceRequest,
    ClearanceCancelRequest,
    ClearanceCreateRequest,
    ClearanceRecord,
    ClearanceRejectRequest,
)
from backend.services import clearance_service

router = APIRouter(prefix="/clearance", tags=["Clearance & Safety Workflow"])


@router.post(
    "/create",
    response_model=ClearanceRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Create maintenance block clearance record",
)
async def create_clearance_record(request: ClearanceCreateRequest):
    """Initializes a new maintenance block request in DRAFT or AI_RECOMMENDED status."""
    existing = clearance_service.get_clearance(request.block_id)
    if existing:
        return existing
    return clearance_service.create_clearance(request)


@router.get(
    "",
    response_model=List[ClearanceRecord],
    summary="List all maintenance block clearance records",
)
async def list_clearances():
    """Returns all active and archived maintenance block clearance records."""
    return clearance_service.list_clearances()


@router.get(
    "/{block_id}",
    response_model=ClearanceRecord,
    summary="Get clearance details and audit history for a block",
)
async def get_clearance_details(block_id: str):
    """Retrieves current review state and immutable audit history for a specific maintenance block."""
    record = clearance_service.get_clearance(block_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clearance record for block '{block_id}' not found.",
        )
    return record


@router.post(
    "/{block_id}/advance",
    response_model=ClearanceRecord,
    summary="Advance clearance through departmental review stages",
)
async def advance_clearance_stage(block_id: str, request: ClearanceAdvanceRequest):
    """
    Advances a block through Operations, Engineering, Traction/OHE, and final Authorization.
    Enforces role permission checks and logs immutable audit records.
    """
    try:
        return clearance_service.advance_clearance(block_id, request)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(perm_err),
        ) from perm_err


@router.post(
    "/{block_id}/reject",
    response_model=ClearanceRecord,
    summary="Reject proposed maintenance block with reason",
)
async def reject_clearance_record(block_id: str, request: ClearanceRejectRequest):
    """Rejects a proposed maintenance block and logs reviewer comments."""
    try:
        return clearance_service.reject_clearance(block_id, request)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(perm_err),
        ) from perm_err


@router.post(
    "/{block_id}/cancel",
    response_model=ClearanceRecord,
    summary="Cancel maintenance block request",
)
async def cancel_clearance_record(block_id: str, request: ClearanceCancelRequest):
    """Cancels a pending maintenance block request."""
    try:
        return clearance_service.cancel_clearance(block_id, request)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(perm_err),
        ) from perm_err
