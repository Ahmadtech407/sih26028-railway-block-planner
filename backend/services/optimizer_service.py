"""
Google OR-Tools CP-SAT Maintenance Block Optimization Service.

Implements multi-factor weighted operational cost optimization for railway maintenance windows:
- Strict zero-overlap hard constraints on Tier 1 & Tier 2 trains with 5-minute safety buffers.
- Accurate regulation delay modeling for Tier 3, 4, 5 trains.
- Multi-tier cost function ranking top feasible alternatives.
- Detailed audit metrics, risk levels, confidence scores, and explanatory reasoning.
"""

from typing import List, Dict, Any, Optional, Tuple
from ortools.sat.python import cp_model

from backend.schemas.api_models import (
    BlockOptimizationRequest,
    BlockOptimizationResponse,
    AlternativeSlot,
    AffectedTrainInfo,
    ConflictCheckRequest,
    ConflictCheckResponse,
    ConflictItem,
    TrainDetails,
)
from backend.services.train_service import get_trains_for_section, min_to_hhmm
from backend.services.platform_service import detect_platform_conflicts
from backend.services.weather_service import get_section_weather

SAFETY_BUFFER_MINUTES = 5

# Weighted Objective Penalties per Tier (Operational Disruption Cost Model)
TIER_FIXED_PENALTY: Dict[int, float] = {
    1: 100000.0,  # Emergency: Extremely High
    2: 50000.0,   # Premium Express: Very High (Hard constraint prevents this)
    3: 300.0,     # Express / Superfast: Medium
    4: 120.0,     # Routine Scheduled Maintenance: Low
    5: 40.0,      # Freight & Goods: Lowest
}

TIER_PER_MINUTE_PENALTY: Dict[int, float] = {
    1: 10000.0,
    2: 5000.0,
    3: 50.0,
    4: 20.0,
    5: 5.0,
}

TOTAL_DELAY_WEIGHT = 10.0
START_TIME_TIEBREAKER_WEIGHT = 0.01


def is_tier1_or_tier2_conflict(start: int, end: int, train: TrainDetails, safety_buffer: int = SAFETY_BUFFER_MINUTES) -> bool:
    """
    Checks if a block [start, end] violates safety isolation buffer with a Tier 1/2 train.
    Condition for compliance: (end + 5 <= train.entry_min) OR (start >= train.exit_min + 5).
    Returns True if there is a conflict/violation.
    """
    if train.priority <= 2:
        is_safely_before = (end + safety_buffer) <= train.entry_min
        is_safely_after = start >= (train.exit_min + safety_buffer)
        return not (is_safely_before or is_safely_after)
    return False


def calculate_train_delay(start: int, end: int, train: TrainDetails, safety_buffer: int = SAFETY_BUFFER_MINUTES) -> int:
    """
    Calculates regulation delay (in minutes) for a train due to maintenance block [start, end].
    If the train's scheduled section window overlaps with the block or requires safety buffer clearance:
    The train must hold at preceding station until the track is cleared at (end + SAFETY_BUFFER_MINUTES).
    """
    track_clear_time = end + safety_buffer

    # Train conflicts if it arrives before track is cleared AND departs after block start
    if train.entry_min < track_clear_time and train.exit_min > start:
        delay = max(0, track_clear_time - train.entry_min)
        return min(delay, 180)  # capped at maximum reasonable regulation threshold
    return 0


def evaluate_slot(
    start: int,
    end: int,
    earliest: int,
    trains: List[TrainDetails],
    safety_buffer: int = SAFETY_BUFFER_MINUTES,
    weather_score: int = 0,
    platform_conflict_count: int = 0,
) -> Tuple[bool, float, List[AffectedTrainInfo], int]:
    """
    Evaluates a candidate maintenance slot [start, end].
    Returns (is_feasible, weighted_cost, affected_trains_list, total_delay_min).
    """
    # 1. Hard Safety Constraints: Tier 1 & 2 Isolation
    for t in trains:
        if t.priority <= 2 and is_tier1_or_tier2_conflict(start, end, t, safety_buffer):
            return False, float("inf"), [], 0

    # 2. Evaluate regulation delays for Tier 3, 4, 5 trains
    affected_trains: List[AffectedTrainInfo] = []
    total_delay = 0
    operational_cost = 0.0

    for t in trains:
        if t.priority > 2:
            delay = calculate_train_delay(start, end, t, safety_buffer)
            if delay > 0:
                total_delay += delay
                # Calculate tier-weighted cost
                fixed_pen = TIER_FIXED_PENALTY.get(t.priority, 50.0)
                per_min_pen = TIER_PER_MINUTE_PENALTY.get(t.priority, 10.0)
                train_cost = fixed_pen + (per_min_pen * delay)
                operational_cost += train_cost

                affected_trains.append(
                    AffectedTrainInfo(
                        train_number=t.train_number,
                        name=t.name,
                        priority=t.priority,
                        scheduled_window=f"{t.entry_time} - {t.exit_time}",
                        delay_minutes=delay,
                        action="REGULATE_HOLD_AT_PRECEDING_STATION",
                        platform_number=t.platform_number,
                    )
                )

    # Add aggregate delay cost and start-time tiebreaker
    operational_cost += (TOTAL_DELAY_WEIGHT * total_delay)
    operational_cost += weather_score * 2.0
    operational_cost += platform_conflict_count * 1000.0
    operational_cost += (START_TIME_TIEBREAKER_WEIGHT * (start - earliest))

    return True, round(operational_cost, 2), affected_trains, total_delay


def determine_risk_level(affected_trains: List[AffectedTrainInfo], total_delay: int) -> str:
    """Classifies operational risk level of a maintenance slot."""
    if not affected_trains or total_delay == 0:
        return "LOW"
    
    has_tier3 = any(t.priority == 3 for t in affected_trains)
    if not has_tier3 or total_delay <= 30:
        return "LOW"
    elif total_delay <= 120:
        return "MEDIUM"
    else:
        return "HIGH"


def calculate_confidence_score(affected_trains: List[AffectedTrainInfo], total_delay: int) -> float:
    """Calculates operational recommendation confidence score percentage."""
    if not affected_trains:
        return 99.0
    
    score = 98.0 - (len(affected_trains) * 4.0) - (total_delay * 0.05)
    return round(max(60.0, min(99.0, score)), 1)


def combine_operational_risk(train_risk: str, weather_risk: str) -> str:
    rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "EXTREME": 3}
    return max((train_risk, weather_risk), key=lambda risk: rank.get(risk, 3))


def generate_reasons(
    start: int,
    end: int,
    duration: int,
    affected_trains: List[AffectedTrainInfo],
    total_delay: int,
    trains: List[TrainDetails],
) -> List[str]:
    """Generates structured reasons explaining why a maintenance window was selected."""
    reasons = [
        "Zero overlap with Tier 1 & Tier 2 High-Speed paths (Vande Bharat, Rajdhani).",
        f"Mandatory {SAFETY_BUFFER_MINUTES}-minute safety isolation buffer strictly enforced at both boundaries.",
        f"Exact requested maintenance duration ({duration} mins) fully allocated ({min_to_hhmm(start)} to {min_to_hhmm(end)}).",
    ]

    if not affected_trains:
        reasons.append("Zero secondary delay incurred across all lower-priority passenger and freight trains.")
    else:
        reasons.append(
            f"Optimized to minimize passenger disruption: total regulation delay constrained to {total_delay} mins across {len(affected_trains)} train(s)."
        )

    return reasons


def check_conflicts(request: ConflictCheckRequest) -> ConflictCheckResponse:
    """Scans a proposed maintenance window against scheduled train paths."""
    trains = get_trains_for_section(request.section_id)
    conflicts: List[ConflictItem] = []

    for t in trains:
        # Direct overlap check
        if max(request.proposed_start_min, t.entry_min) < min(request.proposed_end_min, t.exit_min):
            overlap = min(request.proposed_end_min, t.exit_min) - max(request.proposed_start_min, t.entry_min)
            conflicts.append(
                ConflictItem(
                    train=f"{t.train_number} {t.name}",
                    priority=t.priority,
                    overlap_minutes=max(0, overlap),
                    train_window=f"{t.entry_time} - {t.exit_time}",
                )
            )

    has_critical = any(c.priority <= 2 for c in conflicts)
    has_minor = any(c.priority == 3 for c in conflicts)

    if has_critical:
        status = "CRITICAL_CONFLICT_PREMIUM_TRAINS"
    elif has_minor:
        status = "MINOR_CONFLICT_PASSENGER_TRAINS"
    elif conflicts:
        status = "LOW_CONFLICT_FREIGHT"
    else:
        status = "CLEAR_NO_CONFLICTS"

    return ConflictCheckResponse(
        section_id=request.section_id,
        proposed_window=f"{min_to_hhmm(request.proposed_start_min)} - {min_to_hhmm(request.proposed_end_min)}",
        has_conflict=bool(conflicts),
        conflict_count=len(conflicts),
        conflicting_trains=conflicts,
        status=status,
    )


def solve_maintenance_block(request: BlockOptimizationRequest) -> BlockOptimizationResponse:
    """
    Solves track maintenance block scheduling using Google OR-Tools CP-SAT + Multi-Factor Operational Optimization.
    Finds and ranks the top 5 feasible maintenance slots by lowest weighted operational cost.
    """
    earliest = request.earliest_start_min
    latest = request.latest_end_min
    duration = request.duration_minutes
    trains = get_trains_for_section(request.section_id)
    weather = get_section_weather(
        request.section_id,
        time_min=earliest,
        work_type=request.work_type or "Rail Replacement",
        override_risk=request.override_weather_risk,
    )
    platform_conflicts = detect_platform_conflicts(trains)
    platform_conflict_count = len(platform_conflicts)
    if request.override_platform_conflict:
        platform_conflict_count = max(1, platform_conflict_count)
    weather_buffer = {"LOW": 0, "MEDIUM": 0, "HIGH": 5, "EXTREME": 10}.get(weather.weather_risk.value, 0)
    safety_buffer = SAFETY_BUFFER_MINUTES + weather_buffer

    # 1. Sanity check on time window width
    if earliest + duration > latest:
        return BlockOptimizationResponse(
            block_id=request.block_id,
            section_id=request.section_id,
            status="NO_FEASIBLE_SLOT",
            duration_minutes=duration,
            message=f"Requested maintenance duration ({duration} mins) exceeds the search window ({min_to_hhmm(earliest)} to {min_to_hhmm(latest)}).",
        )

    # 2. OR-Tools CP-SAT Feasibility and Disjunctive Constraint Exploration
    # We evaluate all candidate 5-minute start slots across the search space
    feasible_candidates = []

    for start in range(earliest, latest - duration + 1, 5):
        end = start + duration

        # Formulate CP-SAT model for candidate window
        model = cp_model.CpModel()
        safe = True

        for i, t in enumerate(trains):
            if t.priority <= 2:
                before = model.NewBoolVar(f"before_{i}")
                after = model.NewBoolVar(f"after_{i}")

                model.Add(end + safety_buffer <= t.entry_min).OnlyEnforceIf(before)
                model.Add(start >= t.exit_min + safety_buffer).OnlyEnforceIf(after)
                model.AddBoolOr([before, after])

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 0.05
        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            safe = False

        if not safe:
            continue

        # Mathematical verification of safety buffers
        is_safe, weighted_cost, affected_trains, total_delay = evaluate_slot(
            start=start,
            end=end,
            earliest=earliest,
            trains=trains,
            safety_buffer=safety_buffer,
            weather_score=weather.weather_score,
            platform_conflict_count=platform_conflict_count,
        )

        if is_safe:
            risk_level = determine_risk_level(affected_trains, total_delay)
            confidence = calculate_confidence_score(affected_trains, total_delay)
            risk_level = combine_operational_risk(risk_level, weather.weather_risk.value)
            confidence = round(max(50.0, confidence - (weather.weather_score * 0.1)), 1)
            reasons = generate_reasons(start, end, duration, affected_trains, total_delay, trains)
            reasons.append(f"Weather risk {weather.weather_risk.value} ({weather.weather_score}/100): {weather.weather_reason}")
            if platform_conflict_count:
                reasons.append(f"Platform analysis found {platform_conflict_count} overlapping assignment(s); included in candidate cost.")

            feasible_candidates.append({
                "start": start,
                "end": end,
                "formatted_window": f"{min_to_hhmm(start)} - {min_to_hhmm(end)}",
                "affected_trains": affected_trains,
                "total_delay_min": total_delay,
                "weighted_cost": weighted_cost,
                "risk_level": risk_level,
                "recommendation_confidence_pct": confidence,
                "weather_risk": weather.weather_risk.value,
                "weather_score": weather.weather_score,
                "platform_conflicts": platform_conflict_count,
                "reasons": reasons,
            })

    # 3. Handle infeasible scenario
    if not feasible_candidates:
        return BlockOptimizationResponse(
            block_id=request.block_id,
            section_id=request.section_id,
            status="NO_FEASIBLE_SLOT",
            duration_minutes=duration,
            message="No safe maintenance slot exists within the requested window without violating Tier 1/2 train isolation buffers.",
        )

    # 4. Rank candidates by lowest weighted operational cost
    feasible_candidates.sort(key=lambda x: x["weighted_cost"])

    best = feasible_candidates[0]

    # 5. Build Alternative Slots (Top 5 ranked alternatives)
    alternative_slots: List[AlternativeSlot] = []
    for cand in feasible_candidates[:5]:
        alternative_slots.append(
            AlternativeSlot(
                start_min=cand["start"],
                end_min=cand["end"],
                formatted_window=cand["formatted_window"],
                affected_trains=cand["affected_trains"],
                total_delay_min=cand["total_delay_min"],
                weighted_cost=cand["weighted_cost"],
                risk_level=cand["risk_level"],
                recommendation_confidence_pct=cand["recommendation_confidence_pct"],
                weather_risk=cand["weather_risk"],
                weather_score=cand["weather_score"],
                platform_conflicts=cand["platform_conflicts"],
                reasons=cand["reasons"],
            )
        )

    # 6. Asset availability metric
    total_window_len = latest - earliest
    asset_gain = f"{(duration / total_window_len) * 100:.1f}% of requested time band" if total_window_len > 0 else "100.0%"

    return BlockOptimizationResponse(
        block_id=request.block_id,
        section_id=request.section_id,
        status="OPTIMAL_SCHEDULED",
        allocated_start_min=best["start"],
        allocated_end_min=best["end"],
        formatted_window=best["formatted_window"],
        duration_minutes=duration,
        safety_buffer_minutes=safety_buffer,
        affected_trains=best["affected_trains"],
        total_delay_min=best["total_delay_min"],
        weighted_cost=best["weighted_cost"],
        risk_level=best["risk_level"],
        recommendation_confidence_pct=best["recommendation_confidence_pct"],
        asset_availability_gain=asset_gain,
        weather_risk=weather.weather_risk.value,
        weather_score=weather.weather_score,
        weather_reason=weather.weather_reason,
        weather_source=weather.weather_source,
        weather_observed_at=weather.observed_at,
        platform_conflicts=platform_conflict_count,
        optimization_reason=(
            "Weather and platform constraints included in CP-SAT candidate ranking."
        ),
        reasons=best["reasons"],
        alternatives=alternative_slots,
        message="Optimal conflict-free maintenance window successfully computed and ranked.",
    )
