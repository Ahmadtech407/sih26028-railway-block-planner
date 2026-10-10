"""
Temporary Speed Restriction (TSR) Service.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Calculates physically meaningful sectional run-time dilation resulting from
post-maintenance track settling, ballast consolidation, or engineering caution orders.

PHYSICAL RUN-TIME MODELING:
Partitions railway corridor geometry at every TSR boundary.
Resolves overlapping restrictions by applying strict minimum speed per segment.
Prevents double-counting overlapping restriction distances.
Units:
- Distances: Kilometres (km)
- Speeds: Kilometres per hour (km/h)
- Running times: Minutes and seconds
"""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple
import uuid

from backend import database as db
from backend.schemas.clearance_models import TSRRecord


def calculate_multi_tsr_runtime_dilation(
    corridor_start_km: float,
    corridor_end_km: float,
    normal_speed_kmph: float,
    tsrs: List[Dict[str, Any]],
    accel_loss_min: float = 0.0,
    decel_loss_min: float = 0.0,
) -> Dict[str, Any]:
    """
    Computes rigorous run-time dilation by partitioning geometry at every TSR boundary.
    Resolves overlapping speed restrictions by selecting the minimum speed per disjoint segment.
    Prevents double-counting across overlapping intervals.
    """
    if normal_speed_kmph <= 0:
        raise ValueError(f"Normal permitted speed must be strictly positive (> 0 km/h), got {normal_speed_kmph}.")
    if corridor_end_km < corridor_start_km:
        raise ValueError(f"Corridor end_km ({corridor_end_km}) cannot be less than start_km ({corridor_start_km}).")

    corridor_length = corridor_end_km - corridor_start_km
    if corridor_length <= 0:
        return {
            "corridor_length_km": 0.0,
            "normal_speed_kmph": normal_speed_kmph,
            "total_delay_minutes": 0.0,
            "total_delay_minutes_int": 0,
            "partitioned_segments": [],
            "kinematic_notes": "Zero length corridor; no dilation.",
            "disclaimer": "CALCULATED_RUN_TIME_ONLY: DOES_NOT_CONSTITUTE_ENGINEERING_AUTHORIZATION_TO_LIFT_TSR",
        }

    # Validate and filter input TSRs
    valid_tsrs = []
    for t in tsrs:
        v_tsr = float(t.get("restricted_speed_kmph", t.get("max_speed_kmph", 0.0)))
        if v_tsr <= 0:
            raise ValueError(f"TSR restricted speed must be strictly positive (> 0 km/h), got {v_tsr}.")
        s = float(t.get("start_km", corridor_start_km))
        e = float(t.get("end_km", corridor_end_km))
        if s > e:
            s, e = e, s
        # Clip to corridor
        clipped_s = max(corridor_start_km, s)
        clipped_e = min(corridor_end_km, e)
        if clipped_e > clipped_s:
            valid_tsrs.append({
                "start_km": clipped_s,
                "end_km": clipped_e,
                "speed_kmph": v_tsr,
                "tsr_id": t.get("tsr_id", "ANON_TSR"),
            })

    # Geometry Partitioning: Collect all boundary split points
    boundaries = {corridor_start_km, corridor_end_km}
    for t in valid_tsrs:
        boundaries.add(t["start_km"])
        boundaries.add(t["end_km"])
    sorted_pts = sorted(boundaries)

    partitioned_segments = []
    total_restricted_travel_time_min = 0.0
    total_normal_travel_time_min = 0.0

    for i in range(len(sorted_pts) - 1):
        seg_start = sorted_pts[i]
        seg_end = sorted_pts[i + 1]
        seg_len = seg_end - seg_start
        if seg_len <= 1e-9:
            continue

        # Find all TSRs covering this segment
        covering_speeds = [normal_speed_kmph]
        for t in valid_tsrs:
            if t["start_km"] <= seg_start + 1e-9 and t["end_km"] >= seg_end - 1e-9:
                covering_speeds.append(t["speed_kmph"])

        # Resolve effective speed = minimum applicable speed
        effective_speed = min(covering_speeds)

        t_normal = (seg_len / normal_speed_kmph) * 60.0
        t_restricted = (seg_len / effective_speed) * 60.0
        seg_delay = max(0.0, t_restricted - t_normal)

        total_normal_travel_time_min += t_normal
        total_restricted_travel_time_min += t_restricted

        partitioned_segments.append({
            "start_km": round(seg_start, 3),
            "end_km": round(seg_end, 3),
            "length_km": round(seg_len, 3),
            "effective_speed_kmph": round(effective_speed, 1),
            "is_restricted": effective_speed < normal_speed_kmph,
            "delay_minutes": round(seg_delay, 3),
        })

    steady_state_delay = max(0.0, total_restricted_travel_time_min - total_normal_travel_time_min)
    transition_losses = (accel_loss_min + decel_loss_min) if any(s["is_restricted"] for s in partitioned_segments) else 0.0
    total_delay = steady_state_delay + transition_losses

    return {
        "corridor_length_km": round(corridor_length, 3),
        "normal_speed_kmph": normal_speed_kmph,
        "total_delay_minutes": round(total_delay, 3),
        "total_delay_minutes_int": math.ceil(total_delay) if total_delay > 0 else 0,
        "partitioned_segments": partitioned_segments,
        "kinematic_notes": (
            "CONSTANT_SPEED_ESTIMATE: Assumes piecewise constant velocity across partitioned geometry. "
            "Full physical train dynamics accuracy requires locomotive tractive effort curves and train load tables."
        ),
        "disclaimer": "CALCULATED_RUN_TIME_ONLY: DOES_NOT_CONSTITUTE_ENGINEERING_AUTHORIZATION_TO_LIFT_TSR",
    }


def calculate_tsr_delay_minutes(
    length_km: float,
    normal_speed_kmph: float,
    restricted_speed_kmph: float,
    deceleration_loss_minutes: float = 1.0,
    acceleration_loss_minutes: float = 1.5,
) -> int:
    """
    Computes physical train run-time dilation (delay) caused by traversing a TSR.
    Includes practical acceleration and braking transition allowances.
    """
    if length_km <= 0 or restricted_speed_kmph >= normal_speed_kmph or restricted_speed_kmph <= 0:
        return 0

    res = calculate_multi_tsr_runtime_dilation(
        corridor_start_km=0.0,
        corridor_end_km=length_km,
        normal_speed_kmph=normal_speed_kmph,
        tsrs=[{"start_km": 0.0, "end_km": length_km, "restricted_speed_kmph": restricted_speed_kmph}],
        accel_loss_min=acceleration_loss_minutes,
        decel_loss_min=deceleration_loss_minutes,
    )
    return max(1, res["total_delay_minutes_int"])


def create_post_maintenance_tsr(
    block_id: str,
    section_id: str = "KNP-PRYJ-SEC-B",
    track_id: str = "KNP-PRYJ-DN-MAIN",
    start_km: float = 414.0,
    end_km: float = 422.0,
    initial_speed_kmph: float = 30.0,
    normal_speed_kmph: float = 130.0,
    issued_by: str = "AEN_TRACK_KANPUR",
    effective_from_iso: Optional[str] = None,
    effective_until_iso: Optional[str] = None,
) -> TSRRecord:
    """
    Registers a Temporary Speed Restriction following track maintenance.
    Implements Indian Railways Permanent Way Manual (IRPWM) staged recovery:
    Stage 1: 30 km/h (First 24-48 hours, ballast settling)
    Stage 2: 75 km/h (Days 3-5, initial tamping)
    Stage 3: 100 km/h (Days 6-7, final alignment)
    """
    tsr_id = f"TSR-{datetime.now().strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()
    from_iso = effective_from_iso or now_iso
    until_iso = effective_until_iso or datetime.fromtimestamp(datetime.now().timestamp() + 86400 * 3, timezone.utc).isoformat()

    staged_recovery = [
        {"stage": 1, "max_speed_kmph": initial_speed_kmph, "duration_hours": 48, "status": "ACTIVE"},
        {"stage": 2, "max_speed_kmph": 75.0, "duration_hours": 72, "status": "PENDING"},
        {"stage": 3, "max_speed_kmph": 100.0, "duration_hours": 48, "status": "PENDING"},
    ]

    record = {
        "tsr_id": tsr_id,
        "block_id": block_id,
        "section_id": section_id,
        "track_id": track_id,
        "start_km": start_km,
        "end_km": end_km,
        "max_speed_kmph": initial_speed_kmph,
        "normal_speed_kmph": normal_speed_kmph,
        "effective_from_iso": from_iso,
        "effective_until_iso": until_iso,
        "reason": "Post-maintenance track settling & ballast consolidation (IRPWM Reg 508)",
        "issued_by": issued_by,
        "status": "ACTIVE",
        "staged_recovery_schedule": staged_recovery,
        "created_at": now_iso,
    }
    db.save_tsr_record(record)
    return TSRRecord(**record)


def get_active_tsrs_for_section(section_id: str) -> List[TSRRecord]:
    """Retrieve all active speed restrictions currently dilating section runtimes."""
    records = db.list_active_tsrs(section_id)
    return [TSRRecord(**r) for r in records]


def get_tsr(tsr_id: str) -> Optional[TSRRecord]:
    """Retrieve specific TSR details."""
    data = db.get_tsr_record(tsr_id)
    if not data:
        return None
    return TSRRecord(**data)
