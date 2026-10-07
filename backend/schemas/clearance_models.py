"""
Clearance and Multi-Department Approval Workflow Schemas.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Enforces human-in-the-loop authorization where AI/optimizer output is strictly
AI_RECOMMENDED and cannot bypass required operational/engineering reviews.
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


class UserRoleEnum(str, Enum):
    ADMIN = "ADMIN"
    SECTION_CONTROLLER = "SECTION_CONTROLLER"
    OPERATIONS = "OPERATIONS"
    ENGINEERING_PWAY = "ENGINEERING_PWAY"
    TRACTION_OHE = "TRACTION_OHE"
    VIEWER = "VIEWER"
    SYSTEM = "SYSTEM"


class ApprovalHistoryItem(BaseModel):
    id: Optional[int] = None
    block_id: str
    clearance_id: Optional[int] = None
    action: str = Field(..., description="SUBMIT, RECOMMEND, ADVANCE, APPROVE, REJECT, CANCEL")
    previous_state: Optional[ClearanceStateEnum] = None
    new_state: ClearanceStateEnum
    role: UserRoleEnum
    user_id: str
    comment: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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
