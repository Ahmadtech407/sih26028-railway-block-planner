"""
Tool: OR-Tools Block Optimizer

Uses the Google OR-Tools CP-SAT Solver to compute mathematically optimal
zero-conflict maintenance block windows while respecting train priority
constraints and safety margins.
"""

import json
from typing import Optional

from ortools.sat.python import cp_model

from data.railway_reference_db import TRAIN_SCHEDULE_DB

# Safety buffer in minutes between block clearance and train operations.
# Required for signal setting, point locking, and section isolation.
SAFETY_BUFFER_MINUTES = 5


def run_or_tools_block_optimizer(
    maintenance_requests_json: str,
    train_schedules_json: Optional[str] = None,
    section_id: Optional[str] = None,
) -> str:
    """Solves optimal track block allocation using Google OR-Tools CP-SAT Solver.
    Computes conflict-free maintenance windows that avoid all Tier 1 & Tier 2
    trains and minimize impact on lower-priority traffic.

    Enforces:
    - Non-overlapping intervals against premium trains (priority <= 2).
    - 5-minute safety buffer for signal setting and section isolation.
    - Earliest-start objective to maximize post-maintenance clearance time.

    Args:
        maintenance_requests_json: JSON array of maintenance block requests.
            Each object must have: block_id, section_id, duration_minutes,
            earliest_start, latest_end.
        train_schedules_json: Optional JSON array of train schedules. If not
            provided, the tool uses the internal schedule database.
        section_id: Optional section ID to look up schedules from the database
            when train_schedules_json is not provided.
    """
    # ── Parse inputs ──────────────────────────────────────────────────
    try:
        blocks = json.loads(maintenance_requests_json)
    except Exception as e:
        return json.dumps({
            "status": "ERROR",
            "message": f"Invalid maintenance_requests_json: {e}",
        })

    # Resolve train schedules
    if train_schedules_json:
        try:
            trains = json.loads(train_schedules_json)
        except Exception as e:
            return json.dumps({
                "status": "ERROR",
                "message": f"Invalid train_schedules_json: {e}",
            })
    elif section_id and section_id in TRAIN_SCHEDULE_DB:
        trains = TRAIN_SCHEDULE_DB[section_id]
    elif blocks and blocks[0].get("section_id") in TRAIN_SCHEDULE_DB:
        trains = TRAIN_SCHEDULE_DB[blocks[0]["section_id"]]
    else:
        # Fallback: aggregate all known schedules
        trains = []
        for schedule_list in TRAIN_SCHEDULE_DB.values():
            trains.extend(schedule_list)

    # ── Solve per maintenance request ─────────────────────────────────
    solver_results = {}

    for b in blocks:
        b_id = b["block_id"]
        duration = b["duration_minutes"]
        earliest = b["earliest_start"]
        latest = b["latest_end"]

        # Feasibility pre-check
        if earliest + duration > latest:
            solver_results[b_id] = {
                "status": "INFEASIBLE_WINDOW_TOO_NARROW",
                "message": (
                    f"Duration {duration}min cannot fit between "
                    f"{earliest // 60:02d}:{earliest % 60:02d} and "
                    f"{latest // 60:02d}:{latest % 60:02d}."
                ),
            }
            continue

        model = cp_model.CpModel()

        # ── Decision Variables ────────────────────────────────────────
        start_var = model.new_int_var(
            earliest, latest - duration, f"start_{b_id}"
        )
        end_var = model.new_int_var(
            earliest + duration, latest, f"end_{b_id}"
        )
        model.add(end_var == start_var + duration)

        # ── Objective: Minimize start time (schedule as early as possible) ──
        model.minimize(start_var)

        # ── Hard constraints: Non-overlap with Tier 1 & 2 trains ─────
        for t in trains:
            if t["priority"] <= 2:
                t_entry = t["scheduled_section_entry"]
                t_exit = t["scheduled_section_exit"]

                # Boolean disjunction flags
                block_before_train = model.new_bool_var(
                    f"{b_id}_before_{t['train_number']}"
                )
                train_before_block = model.new_bool_var(
                    f"{b_id}_after_{t['train_number']}"
                )

                # Block must clear (+ safety buffer) before train enters
                model.add(
                    end_var + SAFETY_BUFFER_MINUTES <= t_entry
                ).only_enforce_if(block_before_train)

                # Block can only start (+ safety buffer) after train exits
                model.add(
                    start_var >= t_exit + SAFETY_BUFFER_MINUTES
                ).only_enforce_if(train_before_block)

                # At least one of the two must hold (no overlap)
                model.add_bool_or([block_before_train, train_before_block])

        # ── Solve ─────────────────────────────────────────────────────
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0
        status = solver.solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            opt_start = int(solver.value(start_var))
            opt_end = int(solver.value(end_var))

            # ── Evaluate secondary impacts (Tier 3+ trains) ──────────
            secondary_impacts = []
            for t in trains:
                if t["priority"] > 2:
                    t_entry = t["scheduled_section_entry"]
                    t_exit = t["scheduled_section_exit"]

                    # Check if the allocated block overlaps with this train
                    if max(opt_start, t_entry) < min(opt_end, t_exit):
                        regulation_delay = min(
                            opt_end + SAFETY_BUFFER_MINUTES - t_entry, 60
                        )
                        secondary_impacts.append({
                            "train": t["train_number"],
                            "priority": t["priority"],
                            "estimated_regulation_delay_min": max(0, regulation_delay),
                            "action": "REGULATE_HOLD_AT_PRECEDING_STATION",
                        })

            # ── Asset availability metric ─────────────────────────────
            total_window = latest - earliest
            gain_pct = (duration / total_window * 100) if total_window > 0 else 0

            solver_results[b_id] = {
                "status": "OPTIMAL_SCHEDULED",
                "allocated_start_min": opt_start,
                "allocated_end_min": opt_end,
                "formatted_window": (
                    f"{opt_start // 60:02d}:{opt_start % 60:02d} - "
                    f"{opt_end // 60:02d}:{opt_end % 60:02d}"
                ),
                "duration_minutes": duration,
                "safety_buffer_minutes": SAFETY_BUFFER_MINUTES,
                "premium_train_conflicts": 0,
                "secondary_train_impacts": secondary_impacts,
                "asset_availability_gain": f"{gain_pct:.1f}% of requested period",
                "solver_status": "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
            }
        else:
            solver_results[b_id] = {
                "status": "UNFEASIBLE_NO_WINDOW_FOUND",
                "message": (
                    "High-speed train path density prevents safe block allocation "
                    "within the requested time window without regulatory holds on "
                    "premium trains. Consider extending the window or splitting "
                    "into smaller blocks."
                ),
            }

    return json.dumps(solver_results, indent=2)
