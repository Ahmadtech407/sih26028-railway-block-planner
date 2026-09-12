"""
Unit Tests for Indian Railways Block Optimization Engine.
Tests all critical operational scenarios:
1. 10:00–15:00 window with 120-minute maintenance.
2. Conflict prevention with Vande Bharat Express (Tier 2).
3. Conflict prevention with Rajdhani Express (Tier 2).
4. Infeasible / No feasible window detection.
5. Lower-priority train regulation calculation and cost penalties.
"""

import sys
import os

# Add root directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.schemas.api_models import (
    BlockOptimizationRequest,
    ConflictCheckRequest,
    TrainDetails,
    TrainDirectionEnum,
    TrainStatusEnum,
)
from backend.services.optimizer_service import (
    solve_maintenance_block,
    check_conflicts,
    evaluate_slot,
    is_tier1_or_tier2_conflict,
    calculate_train_delay,
    SAFETY_BUFFER_MINUTES,
)
from backend.services.train_service import get_trains_for_section


def test_standard_120min_maintenance_window():
    """
    Test 1: 10:00–15:00 (600 to 900 min) on KNP-PRYJ-SEC-B with 120-minute block.
    Verifies that:
    - Status is OPTIMAL_SCHEDULED.
    - Result satisfies duration = 120.
    - Selected window does NOT overlap Vande Bharat (630-660) or Rajdhani (720-750) + 5 min buffer.
    - Top 5 alternatives are generated with weighted costs.
    """
    request = BlockOptimizationRequest(
        block_id="MNT-KNP-04",
        section_id="KNP-PRYJ-SEC-B",
        duration_minutes=120,
        earliest_start_min=600,
        latest_end_min=900,
        work_type="Rail Replacement",
    )

    response = solve_maintenance_block(request)

    assert response.status == "OPTIMAL_SCHEDULED", f"Expected OPTIMAL_SCHEDULED, got {response.status}"
    assert response.allocated_start_min is not None
    assert response.allocated_end_min is not None
    assert response.duration_minutes == 120
    assert response.allocated_end_min - response.allocated_start_min == 120

    # Verify safety buffer against Tier 2 trains on KNP-PRYJ-SEC-B:
    # Vande Bharat: entry 630, exit 660
    # Rajdhani: entry 720, exit 750
    start = response.allocated_start_min
    end = response.allocated_end_min

    vb_safe = (end + 5 <= 630) or (start >= 665)
    raj_safe = (end + 5 <= 720) or (start >= 755)

    assert vb_safe, f"Violation: Overlaps Vande Bharat safety zone! Window: {start}-{end}"
    assert raj_safe, f"Violation: Overlaps Rajdhani Express safety zone! Window: {start}-{end}"

    # Verify top 5 alternatives exist and are ranked by weighted cost
    assert len(response.alternatives) > 0
    assert len(response.alternatives) <= 5
    for i in range(len(response.alternatives) - 1):
        assert response.alternatives[i].weighted_cost <= response.alternatives[i + 1].weighted_cost

    print("[PASS] Test 1: Standard 120-minute optimization window passed.")


def test_conflict_prevention_with_vande_bharat():
    """
    Test 2: Specific conflict check with Vande Bharat (10:30-11:00 AM, mins 630-660).
    Verifies that any window overlapping 625-665 is rejected by the hard constraint.
    """
    vb_train = TrainDetails(
        train_number="22436",
        name="Vande Bharat Express",
        priority=2,
        entry_min=630,
        exit_min=660,
        entry_time="10:30",
        exit_time="11:00",
        position_km=414.2,
        speed_kmph=112.0,
        direction=TrainDirectionEnum.UP,
        status=TrainStatusEnum.ON_TIME,
    )

    # Overlapping window: 10:00 to 11:00 (600 to 660) -> end=660 overlaps entry=630
    assert is_tier1_or_tier2_conflict(600, 660, vb_train) is True

    # Overlapping window: 10:45 to 11:45 (645 to 705) -> starts before exit+5 (665)
    assert is_tier1_or_tier2_conflict(645, 705, vb_train) is True

    # Safe window before VB: 09:00 to 10:20 (540 to 620) -> end+5=625 <= entry=630
    assert is_tier1_or_tier2_conflict(540, 620, vb_train) is False

    # Safe window after VB: 11:05 to 12:00 (665 to 720) -> start=665 >= exit+5=665
    assert is_tier1_or_tier2_conflict(665, 720, vb_train) is False

    print("[PASS] Test 2: Vande Bharat isolation buffer conflict prevention passed.")


def test_conflict_prevention_with_rajdhani():
    """
    Test 3: Specific conflict check with Rajdhani Express (12:00-12:30 PM, mins 720-750).
    Verifies that any window overlapping 715-755 is rejected by the hard constraint.
    """
    raj_train = TrainDetails(
        train_number="12302",
        name="Rajdhani Express",
        priority=2,
        entry_min=720,
        exit_min=750,
        entry_time="12:00",
        exit_time="12:30",
        position_km=421.0,
        speed_kmph=105.0,
        direction=TrainDirectionEnum.UP,
        status=TrainStatusEnum.ON_TIME,
    )

    # Window overlapping Rajdhani arrival: 11:30 to 12:30 (690 to 750) -> end=750 > entry=720
    assert is_tier1_or_tier2_conflict(690, 750, raj_train) is True

    # Window starting too soon after Rajdhani: 12:32 to 13:32 (752 to 812) -> start=752 < exit+5=755
    assert is_tier1_or_tier2_conflict(752, 812, raj_train) is True

    # Safe window before Rajdhani: 10:50 to 11:50 (650 to 710) -> end+5=715 <= 720
    assert is_tier1_or_tier2_conflict(650, 710, raj_train) is False

    # Safe window after Rajdhani: 12:35 to 14:35 (755 to 875) -> start=755 >= 755
    assert is_tier1_or_tier2_conflict(755, 875, raj_train) is False

    print("[PASS] Test 3: Rajdhani Express isolation buffer conflict prevention passed.")


def test_no_feasible_window_scenario():
    """
    Test 4: Infeasible window scenarios:
    a) Maintenance duration exceeds search window.
    b) Search window is completely occupied by Tier 2 trains with no gap >= duration.
    Verifies status is NO_FEASIBLE_SLOT and no window is hallucinated.
    """
    # Scenario A: Duration = 120 mins inside 10:00-11:00 (60-minute window)
    req_too_narrow = BlockOptimizationRequest(
        block_id="MNT-IMPOSSIBLE-01",
        section_id="KNP-PRYJ-SEC-B",
        duration_minutes=120,
        earliest_start_min=600,
        latest_end_min=660,
    )
    res_a = solve_maintenance_block(req_too_narrow)
    assert res_a.status == "NO_FEASIBLE_SLOT"
    assert res_a.allocated_start_min is None
    assert res_a.allocated_end_min is None

    # Scenario B: Search window is 10:00–12:00 (600–720, 120 mins total).
    # But Vande Bharat is at 630–660, splitting the 120-min window into [600, 625] (25m) and [665, 715] (50m).
    # Neither gap can fit a 60-minute block.
    req_blocked = BlockOptimizationRequest(
        block_id="MNT-BLOCKED-02",
        section_id="KNP-PRYJ-SEC-B",
        duration_minutes=60,
        earliest_start_min=600,
        latest_end_min=720,
    )
    res_b = solve_maintenance_block(req_blocked)
    assert res_b.status == "NO_FEASIBLE_SLOT"
    assert res_b.allocated_start_min is None
    assert res_b.allocated_end_min is None
    assert "No safe maintenance slot exists" in (res_b.message or "")

    print("[PASS] Test 4: Infeasible / No Feasible Slot detection passed.")


def test_lower_priority_train_regulation_calculation():
    """
    Test 5: Lower-priority train regulation delay calculation:
    For slot 12:35–14:35 (755 to 875 min, track clears at 880):
    - Purushottam Express (Entry 800, Exit 840) must be delayed by (880 - 800) = 80 minutes.
    - Kashi Express (Entry 855, Exit 890) must be delayed by (880 - 855) = 25 minutes.
    - Freight Rake (Entry 690, Exit 730) exits before 755 -> 0 delay.
    """
    purushottam = TrainDetails(
        train_number="12802",
        name="Purushottam Express",
        priority=3,
        entry_min=800,
        exit_min=840,
        entry_time="13:20",
        exit_time="14:00",
        position_km=428.5,
        speed_kmph=92.0,
        direction=TrainDirectionEnum.UP,
        status=TrainStatusEnum.ON_TIME,
    )

    kashi = TrainDetails(
        train_number="15018",
        name="Kashi Express",
        priority=3,
        entry_min=855,
        exit_min=890,
        entry_time="14:15",
        exit_time="14:50",
        position_km=432.1,
        speed_kmph=76.0,
        direction=TrainDirectionEnum.UP,
        status=TrainStatusEnum.ON_TIME,
    )

    freight = TrainDetails(
        train_number="BCNA",
        name="Freight Rake",
        priority=5,
        entry_min=690,
        exit_min=730,
        entry_time="11:30",
        exit_time="12:10",
        position_km=418.0,
        speed_kmph=58.0,
        direction=TrainDirectionEnum.UP,
        status=TrainStatusEnum.REGULATED,
    )

    start = 755
    end = 875  # track clears at 880

    delay_puru = calculate_train_delay(start, end, purushottam)
    delay_kashi = calculate_train_delay(start, end, kashi)
    delay_freight = calculate_train_delay(start, end, freight)

    assert delay_puru == 80, f"Expected 80 min delay for Purushottam, got {delay_puru}"
    assert delay_kashi == 25, f"Expected 25 min delay for Kashi, got {delay_kashi}"
    assert delay_freight == 0, f"Expected 0 min delay for Freight, got {delay_freight}"

    print("[PASS] Test 5: Lower-priority train regulation delay calculations passed.")


if __name__ == "__main__":
    print("=" * 65)
    print(" RUNNING OPTIMIZER UNIT TESTS")
    print("=" * 65)
    test_standard_120min_maintenance_window()
    test_conflict_prevention_with_vande_bharat()
    test_conflict_prevention_with_rajdhani()
    test_no_feasible_window_scenario()
    test_lower_priority_train_regulation_calculation()
    print("=" * 65)
    print(" ALL 5 UNIT TEST SUITES PASSED SUCCESSFULLY [OK]")
    print("=" * 65)
