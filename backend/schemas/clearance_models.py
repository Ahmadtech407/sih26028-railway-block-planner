"""
Clearance and Multi-Department Approval Workflow Schemas.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Enforces human-in-the-loop authorization where AI/optimizer output is strictly
AI_RECOMMENDED and cannot bypass required operational/engineering reviews.
Includes Traction Power (OHE) isolation, Temporary Speed Restriction (TSR), and Machine Logistics.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClearanceStateEnum(str, Enum):
    DRAFT = "DRAFT"
    AI_RECOMMENDED = "AI_RECOMMENDED"
    OPERATIONS_REVIEW = "OPERATIONS_REVIEW"
    ENGINEERING_REVIEW = "ENGINEERING_REVIEW"
    TRACTION_OHE_REVIEW = "TRACTION_OHE_REVIEW"
    AUTHORIZED = "AUTHORIZED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    REOPENED = "REOPENED"


class UserRoleEnum(str, Enum):
    ADMIN = "ADMIN"
    SECTION_CONTROLLER = "SECTION_CONTROLLER"
    OPERATIONS = "OPERATIONS"
    ENGINEERING_PWAY = "ENGINEERING_PWAY"
    TRACTION_OHE = "TRACTION_OHE"
    VIEWER = "VIEWER"
    SYSTEM = "SYSTEM"


class TractionIsolationStateEnum(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    REQUESTED = "REQUESTED"
    ISOLATION_PENDING = "ISOLATION_PENDING"
    ISOLATION_CONFIRMED = "ISOLATION_CONFIRMED"
    EARTHING_CONFIRMED = "EARTHING_CONFIRMED"
    PERMIT_ACTIVE = "PERMIT_ACTIVE"
    WORK_COMPLETE = "WORK_COMPLETE"
    RESTORATION_PENDING = "RESTORATION_PENDING"
    RESTORED = "RESTORED"
    REVOKED = "REVOKED"


class ApprovalHistoryItem(BaseModel):
    id: Optional[int] = None
    block_id: str
    clearance_id: Optional[int] = None
    action: str = Field(..., description="SUBMIT, RECOMMEND, ADVANCE, APPROVE, REJECT, CANCEL, EXPIRE, INVALIDATE, REOPEN")
    previous_state: Optional[ClearanceStateEnum] = None
    new_state: ClearanceStateEnum
    role: UserRoleEnum
    user_id: str
    comment: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TractionPermitRecord(BaseModel):
    permit_id: str = Field(..., example="TPC-OHE-2026-0042")
    block_id: str = Field(..., example="MNT-KNP-04")
    electrical_section_id: str = Field("OHE-KNP-PRYJ-DN", example="OHE-KNP-PRYJ-DN")
    state: TractionIsolationStateEnum = TractionIsolationStateEnum.NOT_REQUESTED
    tpc_officer_id: Optional[str] = None
    power_block_permit_no: Optional[str] = None
    discharge_rod_locations: List[str] = Field(default_factory=list)
    requested_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    permit_issued_at: Optional[str] = None
    work_completed_at: Optional[str] = None
    restored_at: Optional[str] = None
    remarks: Optional[str] = None


class TSRRecord(BaseModel):
    tsr_id: str = Field(..., example="TSR-2026-KNP-01")
    block_id: Optional[str] = None
    section_id: str = Field(..., example="KNP-PRYJ-SEC-B")
    track_id: str = Field("KNP-PRYJ-DN-MAIN", example="KNP-PRYJ-DN-MAIN")
    start_km: float = Field(..., example=414.0)
    end_km: float = Field(..., example=422.0)
    max_speed_kmph: float = Field(..., ge=10.0, le=160.0, example=30.0)
    normal_speed_kmph: float = Field(130.0, example=130.0)
    effective_from_iso: str
    effective_until_iso: str
    reason: str = Field("Post-maintenance track consolidation & ballast settling", example="Post-maintenance track consolidation")
    issued_by: str = Field(..., example="AEN_TRACK_KANPUR")
    status: str = Field("ACTIVE", description="ACTIVE, MODIFIED, CANCELLED")
    staged_recovery_schedule: Optional[List[Dict[str, Any]]] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TrackMachineRecord(BaseModel):
    machine_id: str = Field(..., example="CSM-9021")
    machine_type: str = Field("CSM", description="CSM, BCM, TAMPING, BALLAST_REGULATOR, TOWER_WAGON")
    stabling_station: str = Field("CNB", example="CNB")
    transit_speed_kmph: float = Field(40.0, example=40.0)
    transit_duration_min: int = Field(25, example=25)
    setup_time_min: int = Field(15, example=15)
    clearance_time_min: int = Field(15, example=15)
    assigned_block_id: Optional[str] = None


class ClearanceRecord(BaseModel):
    id: Optional[int] = None
    block_id: str = Field(..., example="MNT-KNP-04")
    section_id: str = Field(..., example="KNP-PRYJ-SEC-B")
    track_id: Optional[str] = Field("KNP-PRYJ-DN-MAIN", example="KNP-PRYJ-DN-MAIN")
    work_type: Optional[str] = Field("Rail Replacement", example="Rail Replacement")
    allocated_window: Optional[str] = Field(None, example="10:30 - 12:30")
    start_min: Optional[int] = None
    end_min: Optional[int] = None
    duration_minutes: int = Field(120, example=120)
    current_state: ClearanceStateEnum = ClearanceStateEnum.DRAFT
    created_by: str = Field("SYSTEM", example="controller_ops_1")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approved_at: Optional[str] = None
    rejected_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    ai_recommendation_note: Optional[str] = None
    # Safety Prerequisite Tracking
    ohe_permit_id: Optional[str] = None
    ohe_isolation_confirmed: bool = False
    signaling_acknowledged: bool = False
    tsr_id: Optional[str] = None
    machine_id: Optional[str] = None
    expires_at: Optional[str] = None
    invalidated_at: Optional[str] = None
    invalidation_reason: Optional[str] = None
    reopened_at: Optional[str] = None
    reopened_by: Optional[str] = None
    data_version: Optional[str] = "v2.0"
    history: List[ApprovalHistoryItem] = Field(default_factory=list)


class ClearanceCreateRequest(BaseModel):
    block_id: str = Field(..., example="MNT-KNP-04")
    section_id: str = Field(..., example="KNP-PRYJ-SEC-B")
    track_id: Optional[str] = Field("KNP-PRYJ-DN-MAIN", example="KNP-PRYJ-DN-MAIN")
    duration_minutes: int = Field(120, ge=15, le=480, example=120)
    start_min: Optional[int] = Field(None, example=630)
    end_min: Optional[int] = Field(None, example=750)
    work_type: Optional[str] = Field("Rail Replacement", example="Rail Replacement")
    created_by: str = Field("operator", example="operator")
    initial_state: ClearanceStateEnum = ClearanceStateEnum.DRAFT
    ai_note: Optional[str] = None
    expires_at: Optional[str] = None


class ClearanceAdvanceRequest(BaseModel):
    target_state: ClearanceStateEnum = Field(..., description="Next state to advance to")
    role: UserRoleEnum = Field(..., description="Operational role executing the action")
    user_id: str = Field(..., description="ID or username of the officer")
    comment: Optional[str] = Field(None, description="Operational justification or review remarks")


class ClearanceRejectRequest(BaseModel):
    role: UserRoleEnum = Field(..., description="Operational role executing rejection")
    user_id: str = Field(..., description="ID or username of the officer")
    reason: str = Field(..., min_length=3, description="Mandatory reason for rejection")


class ClearanceCancelRequest(BaseModel):
    role: UserRoleEnum = Field(..., description="Operational role executing cancellation")
    user_id: str = Field(..., description="ID or username of the officer")
    reason: str = Field(..., min_length=3, description="Mandatory reason for cancellation")


class ClearanceReopenRequest(BaseModel):
    role: UserRoleEnum = Field(..., description="Operational role executing reopening")
    user_id: str = Field(..., description="ID or username of the officer")
    reason: str = Field(..., min_length=3, description="Mandatory operational justification for reopening")


class ClearanceInvalidateRequest(BaseModel):
    role: UserRoleEnum = Field(..., description="Operational role executing invalidation")
    user_id: str = Field(..., description="ID or username of the officer")
    reason: str = Field(..., min_length=3, description="Condition change causing invalidation")

