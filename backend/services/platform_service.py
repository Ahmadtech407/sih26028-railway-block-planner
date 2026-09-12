"""Platform occupancy and conflict analysis over the train feed."""

from typing import List, Tuple

from backend.schemas.api_models import PlatformConflictItem, TrainDetails
from backend.services.train_service import get_trains_for_section, min_to_hhmm
from backend.services import supabase_train_store as supa_store


def _platform_window(train: TrainDetails) -> Tuple[int, int]:
    """Use platform timing when supplied, otherwise the section movement window."""
    def to_minutes(value: str) -> int:
        hour, minute = value.split(":")
        return int(hour) * 60 + int(minute)

    start = to_minutes(train.platform_available_from) if train.platform_available_from else train.entry_min
    end = to_minutes(train.platform_available_until) if train.platform_available_until else train.exit_min
    return start, end


def detect_platform_conflicts(trains: List[TrainDetails]) -> List[PlatformConflictItem]:
    conflicts: List[PlatformConflictItem] = []
    for index, first in enumerate(trains):
        if first.platform_number is None:
            continue
        first_start, first_end = _platform_window(first)
        for second in trains[index + 1:]:
            if second.platform_number != first.platform_number:
                continue
            second_start, second_end = _platform_window(second)
            overlap = min(first_end, second_end) - max(first_start, second_start)
            if overlap <= 0:
                continue
            conflicts.append(
                PlatformConflictItem(
                    platform_number=first.platform_number,
                    train_a=first.train_number,
                    train_b=second.train_number,
                    window_a=f"{min_to_hhmm(first_start)} - {min_to_hhmm(first_end)}",
                    window_b=f"{min_to_hhmm(second_start)} - {min_to_hhmm(second_end)}",
                    overlap_minutes=overlap,
                    severity="CRITICAL" if min(first.priority, second.priority) <= 2 else "MODERATE",
                    reason="Two assigned trains require the same platform during overlapping occupancy windows.",
                )
            )
    return conflicts


def _enrich_with_platform_history(trains: List[TrainDetails]) -> List[TrainDetails]:
    """
    Look up each train's previous platform from Supabase and attach
    previous_platform_number so the passenger app can show change alerts.
    """
    enriched = []
    for train in trains:
        previous = supa_store.get_previous_platform(
            train_number=train.train_number,
            current_platform=train.platform_number,
        )
        if previous is not None:
            # Return a copy with the previous platform filled in
            data = train.model_dump()
            data["previous_platform_number"] = previous
            # Mark the platform_status so the UI triggers the change alert
            if "CHANGE" not in str(data.get("platform_status", "")).upper():
                data["platform_status"] = "PLATFORM_CHANGED"
            enriched.append(TrainDetails(**data))
        else:
            enriched.append(train)
    return enriched


def get_platform_status(section_id: str) -> Tuple[List[TrainDetails], List[PlatformConflictItem]]:
    trains = get_trains_for_section(section_id)
    trains = _enrich_with_platform_history(trains)
    return trains, detect_platform_conflicts(trains)


def get_platform_conflict_response(section_id: str, train_number: str | None = None) -> dict:
    trains, conflicts = get_platform_status(section_id)
    if train_number:
        conflicts = [c for c in conflicts if c.train_a == train_number or c.train_b == train_number]
    assigned = {t.platform_number for t in trains if t.platform_number is not None}
    return {
        "section_id": section_id,
        "has_conflict": bool(conflicts),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "available_platforms": [number for number in range(1, 10) if number not in assigned],
        "status": "PLATFORM_CONFLICT" if conflicts else "PLATFORM_CLEAR",
    }