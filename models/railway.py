"""
Pydantic data models for the Railway Block Planner.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import IntEnum


class TrainPriority(IntEnum):
    """Indian Railways train priority tiers."""
    EMERGENCY = 1        # Emergency track repairs
    PREMIUM_EXPRESS = 2  # Vande Bharat, Rajdhani, Shatabdi, Gatimaan
    EXPRESS = 3          # Express / Superfast / Mail
    MAINTENANCE = 4      # Scheduled routine maintenance blocks
    FREIGHT = 5          # Freight & Goods trains


class MaintenanceRequest(BaseModel):
    """A request to schedule a track maintenance block."""
    block_id: str = Field(
        description="Unique ID for maintenance request (e.g., MNT-KNP-04)"
    )
    section_id: str = Field(
        description="Track section code (e.g., KNP-PRYJ-SEC-B)"
    )
    duration_minutes: int = Field(
        description="Required duration for maintenance in minutes"
    )
    earliest_start: int = Field(
        description="Minutes past midnight for earliest start (e.g., 600 for 10:00 AM)"
    )
    latest_end: int = Field(
        description="Minutes past midnight for latest end time (e.g., 900 for 03:00 PM)"
    )
    work_type: Optional[str] = Field(
        default=None,
        description="Type of maintenance (e.g., Rail Replacement, Tamping, Welding)"
    )


class TrainSchedule(BaseModel):
    """A scheduled train movement through a track section."""
    train_number: str = Field(
        description="Train identifier (e.g., 22436 Vande Bharat)"
    )
    priority: int = Field(
        description="Priority rank (1=highest/emergency, 5=lowest/freight)"
    )
    scheduled_section_entry: int = Field(
        description="Entry time in minutes past midnight"
    )
    scheduled_section_exit: int = Field(
        description="Exit time in minutes past midnight"
    )


class ConflictResult(BaseModel):
    """Result of a conflict check between a maintenance block and train paths."""
    train: str
    priority: int
    overlap_minutes: int


class SectionStatus(BaseModel):
    """Operational status of a track section."""
    status: str
    length_km: float
    max_capacity_tph: int
    signals: str
    active_trains: List[str]


class BlockAllocation(BaseModel):
    """Result of the OR-Tools optimizer for a single maintenance block."""
    status: str
    allocated_start_min: Optional[int] = None
    allocated_end_min: Optional[int] = None
    formatted_window: Optional[str] = None
    duration_minutes: Optional[int] = None
    secondary_train_impacts: Optional[List[dict]] = None
    asset_availability_gain: Optional[str] = None
    message: Optional[str] = None
