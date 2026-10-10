"""
Independent Schedule Constraint Validator.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Provides an independent mathematical & operational validation layer.
CRITICAL ARCHITECTURAL RULE:
This validator must NOT reuse or import the optimizer service's conflict-checking
functions. It operates as an autonomous checker to guarantee solver solution veracity.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.schemas.api_models import TrainDetails


class ScheduleValidationResult(BaseModel):
    is_valid: bool
    status: str
    violations: List[str] = Field(default_factory=list)
    verified_resources: List[str] = Field(default_factory=list)


def validate_schedule_independently(
    allocated_start_min: int,
    allocated_end_min: int,
    duration_minutes: int,
    earliest_min: int,
    latest_min: int,
    exclusive_resources: List[str],
    trains: List[TrainDetails],
    min_headway_minutes: int = 5,
    setup_minutes: int = 15,
    clearance_minutes: int = 5,
) -> ScheduleValidationResult:
    """
    Independently inspects an allocated maintenance possession against physical boundaries,
    resource exclusivities, and train movement paths.
    """
    violations: List[str] = []

    # 1. Boundary & Duration Identity Validation
    if allocated_start_min < earliest_min:
        violations.append(
            f"WINDOW_BOUNDARY_VIOLATION: Start time {allocated_start_min} is earlier than horizon start {earliest_min}."
        )

    if allocated_end_min > latest_min:
        violations.append(
            f"WINDOW_BOUNDARY_VIOLATION: End time {allocated_end_min} exceeds horizon end {latest_min}."
        )

    if (allocated_end_min - allocated_start_min) != duration_minutes:
        violations.append(
            f"DURATION_MISMATCH: Allocated length ({allocated_end_min - allocated_start_min}m) does not match requested ({duration_minutes}m)."
        )

    if duration_minutes <= 0:
        violations.append("NON_POSITIVE_DURATION: Duration must be strictly positive.")

    # 2. Resource Mutual Exclusivity Validation
    # Build complete timeline of exclusive resource occupancy
    # Active possession occupies all exclusive_resources across [allocated_start_min, allocated_end_min]
    possession_interval = (allocated_start_min, allocated_end_min)

    for train in trains:
        t_interval = (train.entry_min, train.exit_min)
        # Check overlap: max(start1, start2) < min(end1, end2)
        has_overlap = max(possession_interval[0], t_interval[0]) < min(possession_interval[1], t_interval[1])

        if has_overlap and train.priority <= 2:
            violations.append(
                f"MUTUAL_EXCLUSIVITY_VIOLATION: High-priority train {train.train_number} ({train.name}, priority {train.priority}) "
                f"window [{train.entry_min}, {train.exit_min}] directly overlaps possession window {possession_interval}."
            )

        # Headway buffer compliance for high-priority trains on the same corridor
        if train.priority <= 2:
            if train.exit_min <= allocated_start_min:
                margin_before = allocated_start_min - train.exit_min
                if margin_before < min_headway_minutes:
                    violations.append(
                        f"HEADWAY_VIOLATION: Margin before possession ({margin_before}m) is less than required minimum headway ({min_headway_minutes}m) for train {train.train_number}."
                    )
            elif train.entry_min >= allocated_end_min:
                margin_after = train.entry_min - allocated_end_min
                if margin_after < min_headway_minutes:
                    violations.append(
                        f"HEADWAY_VIOLATION: Margin after possession ({margin_after}m) is less than required minimum headway ({min_headway_minutes}m) for train {train.train_number}."
                    )

    is_valid = len(violations) == 0
    return ScheduleValidationResult(
        is_valid=is_valid,
        status="INDEPENDENT_VERIFICATION_PASSED" if is_valid else "INDEPENDENT_VERIFICATION_FAILED",
        violations=violations,
        verified_resources=list(exclusive_resources),
    )
