"""
Traction Power (OHE) Isolation & Permit-to-Work Service.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Enforces:
1. State Machine:
   NOT_REQUESTED -> REQUESTED -> ISOLATION_PENDING -> ISOLATION_CONFIRMED ->
   EARTHING_CONFIRMED -> PERMIT_ACTIVE -> WORK_COMPLETE -> RESTORATION_PENDING -> RESTORED
2. Mandatory Pre-requisite Gate:
   Track maintenance requiring 25 kV AC OHE de-energization cannot be authorized
   without an active, verified Permit-to-Work from the Traction Power Controller (TPC).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from backend import database as db
from backend.schemas.clearance_models import (
    TractionIsolationStateEnum,
    TractionPermitRecord,
)

VALID_TRANSITIONS = {
    TractionIsolationStateEnum.NOT_REQUESTED: [TractionIsolationStateEnum.REQUESTED],
    TractionIsolationStateEnum.REQUESTED: [TractionIsolationStateEnum.ISOLATION_PENDING],
    TractionIsolationStateEnum.ISOLATION_PENDING: [TractionIsolationStateEnum.ISOLATION_CONFIRMED],
    TractionIsolationStateEnum.ISOLATION_CONFIRMED: [TractionIsolationStateEnum.EARTHING_CONFIRMED],
    TractionIsolationStateEnum.EARTHING_CONFIRMED: [TractionIsolationStateEnum.PERMIT_ACTIVE],
    TractionIsolationStateEnum.PERMIT_ACTIVE: [TractionIsolationStateEnum.WORK_COMPLETE, TractionIsolationStateEnum.REVOKED],
    TractionIsolationStateEnum.WORK_COMPLETE: [TractionIsolationStateEnum.RESTORATION_PENDING],
    TractionIsolationStateEnum.RESTORATION_PENDING: [TractionIsolationStateEnum.RESTORED],
    TractionIsolationStateEnum.REVOKED: [TractionIsolationStateEnum.REQUESTED],
}


def request_ohe_isolation(
    block_id: str,
    electrical_section_id: str = "OHE-KNP-PRYJ-DN",
    tpc_officer_id: Optional[str] = None,
    remarks: Optional[str] = None,
) -> TractionPermitRecord:
    """Initiates an OHE power block isolation request to the Traction Power Controller."""
    permit_id = f"TPC-OHE-{datetime.now().strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "permit_id": permit_id,
        "block_id": block_id,
        "electrical_section_id": electrical_section_id,
        "state": TractionIsolationStateEnum.REQUESTED.value,
        "tpc_officer_id": tpc_officer_id or "TPC_CONTROL_KANPUR",
        "power_block_permit_no": None,
        "discharge_rod_locations": [],
        "requested_at": now_iso,
        "confirmed_at": None,
        "permit_issued_at": None,
        "work_completed_at": None,
        "restored_at": None,
        "remarks": remarks or "Scheduled 25 kV AC OHE de-energization requested for track possession",
    }
    db.save_ohe_permit(record)
    return TractionPermitRecord(**record)


def advance_ohe_state(
    permit_id: str,
    target_state: TractionIsolationStateEnum,
    officer_id: str,
    permit_number: Optional[str] = None,
    discharge_locations: Optional[List[str]] = None,
    remarks: Optional[str] = None,
) -> TractionPermitRecord:
    """Advances traction power block state with operational verification."""
    data = db.get_ohe_permit(permit_id)
    if not data:
        raise ValueError(f"OHE Permit '{permit_id}' does not exist.")

    current_state = TractionIsolationStateEnum(data["state"])
    allowed = VALID_TRANSITIONS.get(current_state, [])
    if target_state not in allowed:
        raise ValueError(
            f"Invalid OHE state transition from '{current_state.value}' to '{target_state.value}'. "
            f"Permitted next states: {[s.value for s in allowed]}"
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    data["state"] = target_state.value
    if remarks:
        data["remarks"] = remarks

    if target_state == TractionIsolationStateEnum.ISOLATION_CONFIRMED:
        data["confirmed_at"] = now_iso
    elif target_state == TractionIsolationStateEnum.EARTHING_CONFIRMED:
        if discharge_locations:
            data["discharge_rod_locations"] = discharge_locations
    elif target_state == TractionIsolationStateEnum.PERMIT_ACTIVE:
        data["permit_issued_at"] = now_iso
        data["power_block_permit_no"] = permit_number or f"PB-{datetime.now().strftime('%d%m%y')}-{uuid.uuid4().hex[:4].upper()}"
        data["tpc_officer_id"] = officer_id
    elif target_state == TractionIsolationStateEnum.WORK_COMPLETE:
        data["work_completed_at"] = now_iso
    elif target_state == TractionIsolationStateEnum.RESTORED:
        data["restored_at"] = now_iso

    db.save_ohe_permit(data)
    return TractionPermitRecord(**data)


def get_ohe_permit(permit_id: str) -> Optional[TractionPermitRecord]:
    """Retrieve OHE permit details."""
    data = db.get_ohe_permit(permit_id)
    if not data:
        return None
    return TractionPermitRecord(**data)


def get_permit_for_block(block_id: str) -> Optional[TractionPermitRecord]:
    """Retrieve active or latest OHE permit for a block."""
    data = db.get_ohe_permit_by_block(block_id)
    if not data:
        return None
    return TractionPermitRecord(**data)


def is_ohe_permit_active(block_id: str) -> bool:
    """Returns True ONLY if a verified Permit-to-Work is currently ACTIVE."""
    permit = get_permit_for_block(block_id)
    if not permit:
        return False
    return permit.state == TractionIsolationStateEnum.PERMIT_ACTIVE
