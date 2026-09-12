"""
Tool: Check Track Conflicts

Checks if a proposed maintenance block window overlaps with scheduled
high-priority train paths on a given section.
"""

import json
from data.railway_reference_db import TRAIN_SCHEDULE_DB


def check_track_conflicts(
    section_id: str,
    proposed_start_min: int,
    proposed_end_min: int,
) -> str:
    """Checks if a proposed maintenance block window overlaps with any scheduled
    train paths on the given section. Returns all conflicting trains with their
    priority levels and overlap durations.

    Args:
        section_id: The track section code (e.g., 'KNP-PRYJ-SEC-B').
        proposed_start_min: Proposed block start time in minutes past midnight (0-1440).
        proposed_end_min: Proposed block end time in minutes past midnight (0-1440).
    """
    trains = TRAIN_SCHEDULE_DB.get(section_id, [])

    if not trains:
        return json.dumps({
            "section_id": section_id,
            "has_conflict": False,
            "conflicting_trains": [],
            "status": "NO_TRAINS_SCHEDULED",
            "note": f"No train schedules found for section '{section_id}'.",
        })

    conflicts = []
    for t in trains:
        entry = t["scheduled_section_entry"]
        exit_ = t["scheduled_section_exit"]

        # Check interval overlap: max(start1, start2) < min(end1, end2)
        overlap_start = max(proposed_start_min, entry)
        overlap_end = min(proposed_end_min, exit_)

        if overlap_start < overlap_end:
            conflicts.append({
                "train": t["train_number"],
                "priority": t["priority"],
                "overlap_minutes": overlap_end - overlap_start,
                "train_window": f"{entry // 60:02d}:{entry % 60:02d} - {exit_ // 60:02d}:{exit_ % 60:02d}",
            })

    # Determine status severity
    has_critical = any(c["priority"] <= 2 for c in conflicts)
    has_minor = any(c["priority"] == 3 for c in conflicts)

    if has_critical:
        status = "CRITICAL_CONFLICT_PREMIUM_TRAINS"
    elif has_minor:
        status = "MINOR_CONFLICT_EXPRESS_TRAINS"
    elif conflicts:
        status = "LOW_CONFLICT_FREIGHT_ONLY"
    else:
        status = "CLEAR_NO_CONFLICTS"

    result = {
        "section_id": section_id,
        "proposed_window": (
            f"{proposed_start_min // 60:02d}:{proposed_start_min % 60:02d} - "
            f"{proposed_end_min // 60:02d}:{proposed_end_min % 60:02d}"
        ),
        "has_conflict": len(conflicts) > 0,
        "conflict_count": len(conflicts),
        "conflicting_trains": conflicts,
        "status": status,
    }
    return json.dumps(result, indent=2)
