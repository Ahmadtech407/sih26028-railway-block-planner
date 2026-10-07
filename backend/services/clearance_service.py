"""
Clearance and Multi-Department Approval Workflow Service.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Enforces:
1. Hard Safety Gate: AI recommendations are strictly advisory (AI_RECOMMENDED).
2. Strict State Machine: DRAFT -> AI_RECOMMENDED -> OPERATIONS_REVIEW ->
   ENGINEERING_REVIEW -> TRACTION_OHE_REVIEW -> AUTHORIZED -> APPROVED.
3. Role-Based Access Control (RBAC): Every transition requires verified role authority.
4. Persistent, Immutable Audit Trail: Who, What, When, Why recorded to persistent database.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend import database as db
from backend.schemas.clearance_models import (
    ApprovalHistoryItem,
    ClearanceAdvanceRequest,
    ClearanceCancelRequest,
    ClearanceCreateRequest,
    ClearanceRecord,
    ClearanceRejectRequest,
    ClearanceStateEnum,
    UserRoleEnum,
)

# Role authority matrix for permitted state transitions
# Key: (from_state, to_state) -> allowed roles
PERMITTED_TRANSITIONS: Dict[Tuple[ClearanceStateEnum, ClearanceStateEnum], List[UserRoleEnum]] = {
    # Draft to AI recommendation (produced by optimizer or submitted plan)
    (ClearanceStateEnum.DRAFT, ClearanceStateEnum.AI_RECOMMENDED): [
        UserRoleEnum.SECTION_CONTROLLER,
        UserRoleEnum.OPERATIONS,
        UserRoleEnum.ADMIN,
    ],
    # Direct review start if AI recommendation was skipped/manual
    (ClearanceStateEnum.DRAFT, ClearanceStateEnum.OPERATIONS_REVIEW): [
        UserRoleEnum.SECTION_CONTROLLER,
        UserRoleEnum.OPERATIONS,
        UserRoleEnum.ADMIN,
    ],
    # AI Recommended to Operations Review
    (ClearanceStateEnum.AI_RECOMMENDED, ClearanceStateEnum.OPERATIONS_REVIEW): [
        UserRoleEnum.OPERATIONS,
        UserRoleEnum.SECTION_CONTROLLER,
        UserRoleEnum.ADMIN,
    ],
    # Operations Review to Engineering P-Way Review
    (ClearanceStateEnum.OPERATIONS_REVIEW, ClearanceStateEnum.ENGINEERING_REVIEW): [
        UserRoleEnum.OPERATIONS,
        UserRoleEnum.SECTION_CONTROLLER,
        UserRoleEnum.ADMIN,
    ],
    # Engineering Review to Traction/OHE Review
    (ClearanceStateEnum.ENGINEERING_REVIEW, ClearanceStateEnum.TRACTION_OHE_REVIEW): [
        UserRoleEnum.ENGINEERING_PWAY,
        UserRoleEnum.ADMIN,
    ],
    # Traction/OHE Review to Section Controller Final Authorization
    (ClearanceStateEnum.TRACTION_OHE_REVIEW, ClearanceStateEnum.AUTHORIZED): [
        UserRoleEnum.TRACTION_OHE,
        UserRoleEnum.ADMIN,
    ],
    # Final Section Controller / Admin approval to officially permit track possession
    (ClearanceStateEnum.AUTHORIZED, ClearanceStateEnum.APPROVED): [
        UserRoleEnum.SECTION_CONTROLLER,
        UserRoleEnum.ADMIN,
    ],
}

# Terminal or rejection transitions permitted from active in-review states
REJECTION_SOURCES = [
    ClearanceStateEnum.AI_RECOMMENDED,
    ClearanceStateEnum.OPERATIONS_REVIEW,
    ClearanceStateEnum.ENGINEERING_REVIEW,
    ClearanceStateEnum.TRACTION_OHE_REVIEW,
    ClearanceStateEnum.AUTHORIZED,
]

CANCELLATION_SOURCES = [
    ClearanceStateEnum.DRAFT,
    ClearanceStateEnum.AI_RECOMMENDED,
    ClearanceStateEnum.OPERATIONS_REVIEW,
    ClearanceStateEnum.ENGINEERING_REVIEW,
    ClearanceStateEnum.TRACTION_OHE_REVIEW,
    ClearanceStateEnum.AUTHORIZED,
]


def create_clearance(request: ClearanceCreateRequest) -> ClearanceRecord:
    """Create and persist a new maintenance block clearance record."""
    now_iso = datetime.now(timezone.utc).isoformat()
    initial_state = request.initial_state

    record_dict = {
        "block_id": request.block_id,
        "section_id": request.section_id,
        "track_id": request.track_id or "KNP-PRYJ-DN-MAIN",
        "work_type": request.work_type or "Track Maintenance",
        "allocated_window": (
            f"{request.start_min // 60:02d}:{request.start_min % 60:02d} - {request.end_min // 60:02d}:{request.end_min % 60:02d}"
            if request.start_min is not None and request.end_min is not None
            else None
        ),
        "start_min": request.start_min,
        "end_min": request.end_min,
        "duration_minutes": request.duration_minutes,
        "current_state": initial_state.value,
        "created_by": request.created_by,
        "created_at": now_iso,
        "updated_at": now_iso,
        "ai_recommendation_note": request.ai_note,
    }

    db.save_clearance_record(record_dict)

    # Record initial audit entry
    db.add_approval_history({
        "block_id": request.block_id,
        "action": "CREATE" if initial_state == ClearanceStateEnum.DRAFT else "AI_RECOMMEND",
        "previous_state": None,
        "new_state": initial_state.value,
        "role": "SYSTEM",
        "user_id": request.created_by,
        "comment": request.ai_note or f"Maintenance clearance initialized with state {initial_state.value}",
        "timestamp": now_iso,
    })

    record_data = db.get_clearance_record(request.block_id)
    return ClearanceRecord(**record_data)


def get_clearance(block_id: str) -> Optional[ClearanceRecord]:
    """Retrieve persistent clearance record including chronological audit history."""
    data = db.get_clearance_record(block_id)
    if not data:
        return None
    return ClearanceRecord(**data)


def list_clearances() -> List[ClearanceRecord]:
    """List all persistent maintenance block clearance records."""
    records = db.list_clearance_records()
    return [ClearanceRecord(**r) for r in records]


def advance_clearance(block_id: str, request: ClearanceAdvanceRequest) -> ClearanceRecord:
    """
    Advance a clearance record along the multi-department review pipeline.
    Validates role authority and enforces valid state machine transitions.
    """
    record_data = db.get_clearance_record(block_id)
    if not record_data:
        raise ValueError(f"Clearance record for block '{block_id}' does not exist.")

    current_state = ClearanceStateEnum(record_data["current_state"])
    target_state = request.target_state
    role = request.role

    # Role validation against permitted transition
    transition_key = (current_state, target_state)
    allowed_roles = PERMITTED_TRANSITIONS.get(transition_key)

    if allowed_roles is None:
        raise ValueError(
            f"Invalid clearance transition: cannot move from '{current_state.value}' to '{target_state.value}'. "
            "Must follow sequential review: DRAFT -> AI_RECOMMENDED -> OPERATIONS_REVIEW -> "
            "ENGINEERING_REVIEW -> TRACTION_OHE_REVIEW -> AUTHORIZED -> APPROVED."
        )

    if role not in allowed_roles:
        allowed_names = [r.value for r in allowed_roles]
        raise PermissionError(
            f"Role '{role.value}' is not authorized to advance clearance from '{current_state.value}' to '{target_state.value}'. "
            f"Required role(s): {', '.join(allowed_names)}."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    record_data["current_state"] = target_state.value
    record_data["updated_at"] = now_iso
    if target_state == ClearanceStateEnum.APPROVED:
        record_data["approved_at"] = now_iso

    db.save_clearance_record(record_data)

    # Append immutable audit entry
    db.add_approval_history({
        "block_id": block_id,
        "action": "ADVANCE_REVIEW" if target_state != ClearanceStateEnum.APPROVED else "FINAL_AUTHORIZATION",
        "previous_state": current_state.value,
        "new_state": target_state.value,
        "role": role.value,
        "user_id": request.user_id,
        "comment": request.comment or f"Advanced to {target_state.value}",
        "timestamp": now_iso,
    })

    updated = db.get_clearance_record(block_id)
    return ClearanceRecord(**updated)


def reject_clearance(block_id: str, request: ClearanceRejectRequest) -> ClearanceRecord:
    """Reject a proposed maintenance block window with operational justification."""
    record_data = db.get_clearance_record(block_id)
    if not record_data:
        raise ValueError(f"Clearance record for block '{block_id}' does not exist.")

    current_state = ClearanceStateEnum(record_data["current_state"])
    if current_state not in REJECTION_SOURCES:
        raise ValueError(f"Cannot reject block in terminal or inactive state '{current_state.value}'.")

    if request.role == UserRoleEnum.VIEWER:
        raise PermissionError("Role 'VIEWER' is not authorized to reject maintenance blocks.")

    now_iso = datetime.now(timezone.utc).isoformat()
    record_data["current_state"] = ClearanceStateEnum.REJECTED.value
    record_data["rejected_at"] = now_iso
    record_data["updated_at"] = now_iso

    db.save_clearance_record(record_data)

    db.add_approval_history({
        "block_id": block_id,
        "action": "REJECT",
        "previous_state": current_state.value,
        "new_state": ClearanceStateEnum.REJECTED.value,
        "role": request.role.value,
        "user_id": request.user_id,
        "comment": request.reason,
        "timestamp": now_iso,
    })

    updated = db.get_clearance_record(block_id)
    return ClearanceRecord(**updated)


def cancel_clearance(block_id: str, request: ClearanceCancelRequest) -> ClearanceRecord:
    """Cancel a proposed maintenance block prior to approval."""
    record_data = db.get_clearance_record(block_id)
    if not record_data:
        raise ValueError(f"Clearance record for block '{block_id}' does not exist.")

    current_state = ClearanceStateEnum(record_data["current_state"])
    if current_state not in CANCELLATION_SOURCES:
        raise ValueError(f"Cannot cancel block in state '{current_state.value}'.")

    if request.role not in [UserRoleEnum.SECTION_CONTROLLER, UserRoleEnum.ADMIN, UserRoleEnum.OPERATIONS]:
        raise PermissionError(f"Role '{request.role.value}' is not authorized to cancel clearance requests.")

    now_iso = datetime.now(timezone.utc).isoformat()
    record_data["current_state"] = ClearanceStateEnum.CANCELLED.value
    record_data["cancelled_at"] = now_iso
    record_data["updated_at"] = now_iso

    db.save_clearance_record(record_data)

    db.add_approval_history({
        "block_id": block_id,
        "action": "CANCEL",
        "previous_state": current_state.value,
        "new_state": ClearanceStateEnum.CANCELLED.value,
        "role": request.role.value,
        "user_id": request.user_id,
        "comment": request.reason,
        "timestamp": now_iso,
    })

    updated = db.get_clearance_record(block_id)
    return ClearanceRecord(**updated)
