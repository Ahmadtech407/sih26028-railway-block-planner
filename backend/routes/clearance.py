"""
Clearance and Multi-Department Review API Routes.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Provides endpoints to manage the human-in-the-loop clearance lifecycle,
Traction Power (OHE) isolation permits, TSRs, and Signaling boundary.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.schemas.clearance_models import (
    ClearanceAdvanceRequest,
    ClearanceCancelRequest,
    ClearanceCreateRequest,
    ClearanceInvalidateRequest,
    ClearanceRecord,
    ClearanceRejectRequest,
    ClearanceReopenRequest,
    TractionIsolationStateEnum,
    TractionPermitRecord,
    TSRRecord,
)
from backend.services import clearance_service, traction_service, tsr_service
from backend.services.signaling_adapter import signaling_adapter, InterlockingStatus

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
    "/signaling/status",
    response_model=InterlockingStatus,
    summary="Check signaling and interlocking boundary connection",
)
async def get_signaling_boundary_status():
    """Returns interlocking adapter connection status and safety disclaimer."""
    return signaling_adapter.get_status()


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
    Enforces role permission checks, separation of duties, and verified prerequisites.
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


@router.post(
    "/{block_id}/reopen",
    response_model=ClearanceRecord,
    summary="Reopen rejected, cancelled, expired or invalidated block",
)
async def reopen_clearance_record(block_id: str, request: ClearanceReopenRequest):
    """Reopens a terminal or invalidated block for fresh operational evaluation."""
    try:
        return clearance_service.reopen_clearance(block_id, request)
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
    "/{block_id}/invalidate",
    response_model=ClearanceRecord,
    summary="Invalidate clearance when track or delay conditions change",
)
async def invalidate_clearance_record(block_id: str, request: ClearanceInvalidateRequest):
    """Invalidates an in-review or approved clearance due to material operational disruption."""
    try:
        return clearance_service.invalidate_clearance(block_id, request)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err


# -------------------------------------------------------------------
# OHE Traction Isolation Routes
# -------------------------------------------------------------------

@router.post(
    "/ohe/{block_id}/request",
    response_model=TractionPermitRecord,
    summary="Request 25 kV AC OHE Traction Power Block",
)
async def request_ohe_permit(block_id: str, electrical_section_id: str = "OHE-KNP-PRYJ-DN", remarks: Optional[str] = None):
    """Initiates official traction isolation request to the Traction Power Controller (TPC)."""
    return traction_service.request_ohe_isolation(block_id, electrical_section_id=electrical_section_id, remarks=remarks)


@router.post(
    "/ohe/{permit_id}/advance",
    response_model=TractionPermitRecord,
    summary="Advance OHE traction isolation workflow",
)
async def advance_ohe_permit(
    permit_id: str,
    target_state: TractionIsolationStateEnum,
    officer_id: str = "TPC_OFFICER_1",
    permit_number: Optional[str] = None,
    discharge_locations: Optional[List[str]] = None,
    remarks: Optional[str] = None,
):
    """Advances traction permit state (e.g. to ISOLATION_CONFIRMED, EARTHING_CONFIRMED, PERMIT_ACTIVE)."""
    try:
        return traction_service.advance_ohe_state(
            permit_id,
            target_state=target_state,
            officer_id=officer_id,
            permit_number=permit_number,
            discharge_locations=discharge_locations,
            remarks=remarks,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err)) from val_err


@router.get(
    "/ohe/{block_id}/status",
    response_model=Optional[TractionPermitRecord],
    summary="Get OHE permit status for a maintenance block",
)
async def get_ohe_status_for_block(block_id: str):
    """Retrieves current traction power permit associated with a block."""
    return traction_service.get_permit_for_block(block_id)


# -------------------------------------------------------------------
# Temporary Speed Restriction (TSR) Routes
# -------------------------------------------------------------------

@router.get(
    "/tsr/{section_id}",
    response_model=List[TSRRecord],
    summary="List active Temporary Speed Restrictions for a section",
)
async def get_active_tsrs(section_id: str):
    """Retrieves all active speed restrictions dilating section runtimes."""
    return tsr_service.get_active_tsrs_for_section(section_id)
