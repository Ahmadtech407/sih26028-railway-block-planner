"""
Production Hardening V2 Test Suite.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Validates:
1. Infrastructure Configuration Rigour: Fails explicitly on missing/unvalidated section config.
2. CP-SAT Solver Fidelity:
   - Valid boolean reified exclusion and AddBoolOr
   - Distinct alternative slot generation without hardcoded 15m buffer
   - Independent constraint validation
   - Proper status classification (OPTIMAL vs FEASIBLE vs INFEASIBLE)
3. Multi-Segment Physical TSR Engine:
   - Geometric boundary partitioning
   - Minimum applicable speed resolution without double-counting
   - Boundary cases: zero-length, invalid/negative speed, exceeding permitted speed
   - Advisory declaration integrity
4. Transactional Safety & Clearance Controls:
   - Separation of duties (creator != approver)
   - OHE permit validation (revocation, section matching, authoritative sign-off)
   - Signaling integration boundary (NOT_CONNECTED)
5. Database Durability & Online Backup/Recovery.
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend import database as db
from backend.schemas.api_models import (
    BlockOptimizationRequest,
    TrainDetails,
)
from backend.schemas.clearance_models import (
    ClearanceAdvanceRequest,
    ClearanceCreateRequest,
    ClearanceStateEnum,
    TractionIsolationStateEnum,
    UserRoleEnum,
)
from backend.schemas.topology_models import InfrastructureConfigError
from backend.services import (
    clearance_service,
    optimizer_service,
    section_service,
    traction_service,
    tsr_service,
)
from backend.services.schedule_validator import validate_schedule_independently
from backend.services.signaling_adapter import signaling_adapter
from backend.scripts.db_backup_restore import perform_sqlite_online_backup, restore_sqlite_backup


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. INFRASTRUCTURE CONFIGURATION RIGOUR
# ==============================================================================

def test_missing_infrastructure_config_produces_explicit_planning_failure():
    """Verify that unconfigured corridor sections fail explicitly without assuming defaults."""
    req = BlockOptimizationRequest(
        block_id="TEST-UNKNOWN-CORRIDOR",
        section_id="UNKNOWN-SECTION-99",
        duration_minutes=60,
        earliest_start_min=600,
        latest_end_min=900,
    )
    res = optimizer_service.solve_maintenance_block(req)
    assert res.status == "PLANNING_ERROR_MISSING_INFRASTRUCTURE_CONFIG"
    assert res.solver_status == "UNKNOWN"
    assert "PLANNING_ERROR_MISSING_INFRASTRUCTURE_CONFIG" in res.message


def test_validated_infrastructure_config_resolves_headway():
    """Verify that known sections resolve validated parameters explicitly."""
    cfg = section_service.get_section_infrastructure_config("KNP-PRYJ-SEC-B")
    assert cfg.minimum_headway_minutes == 5
    assert cfg.length_km == 42.5
    assert len(cfg.exclusive_resources) >= 2
    assert cfg.is_validated is True


# ==============================================================================
# 2. CP-SAT SOLVER MULTI-RESOURCE FIDELITY & INDEPENDENT VALIDATOR
# ==============================================================================

def test_cpsat_solver_distinct_alternatives_and_status_fidelity():
    """Verify CP-SAT produces valid, distinct alternatives with solver status fidelity."""
    req = BlockOptimizationRequest(
        block_id="MNT-CP-SAT-CORRECT",
        section_id="KNP-PRYJ-SEC-B",
        duration_minutes=90,
        earliest_start_min=600,
        latest_end_min=1080,
        min_separation_minutes=20,  # Configurable separation parameter
    )
    res = optimizer_service.solve_maintenance_block(req)
    assert res.status in ("OPTIMAL_SCHEDULED", "FEASIBLE_SUBOPTIMAL_SCHEDULED")
    assert res.solver_status in ("OPTIMAL", "FEASIBLE")
    assert res.independent_validation_status == "INDEPENDENT_VERIFICATION_PASSED"
    assert res.allocated_start_min is not None
    assert res.allocated_end_min is not None
    assert res.allocated_end_min - res.allocated_start_min == 90

    # Verify alternative distinctness
    if len(res.alternatives) > 1:
        prev_cand = res.alternatives[0]
        for next_cand in res.alternatives[1:]:
            # Must satisfy configurable separation (>= 20 mins)
            assert (
                next_cand.start_min >= prev_cand.end_min + 20
                or next_cand.end_min <= prev_cand.start_min - 20
            )


def test_cpsat_infeasible_horizon_reports_no_feasible_slot():
    """Verify that impossible horizons return NO_FEASIBLE_SLOT with INFEASIBLE solver status."""
    req = BlockOptimizationRequest(
        block_id="MNT-INFEASIBLE",
        section_id="KNP-PRYJ-SEC-B",
        duration_minutes=180,
        earliest_start_min=600,
        latest_end_min=700,  # Only 100 min window for a 180 min block
    )
    res = optimizer_service.solve_maintenance_block(req)
    assert res.status == "NO_FEASIBLE_SLOT"
    assert res.solver_status == "INFEASIBLE"


def test_independent_schedule_validator_detects_injected_conflict():
    """Verify independent validator detects an illegal schedule without relying on optimizer."""
    fake_train = TrainDetails(
        train_number="12301",
        name="Howrah Rajdhani",
        priority=2,
        entry_time="11:00",
        exit_time="11:30",
        entry_min=660,
        exit_min=690,
        status="ON TIME",
        position_km=420.0,
        speed_kmph=130.0,
        platform_number=1,
    )
    # Possession [650, 710] directly overlaps train [660, 690]
    val = validate_schedule_independently(
        allocated_start_min=650,
        allocated_end_min=710,
        duration_minutes=60,
        earliest_min=600,
        latest_min=900,
        exclusive_resources=["TRACK_DN_MAIN_400_442"],
        trains=[fake_train],
        min_headway_minutes=5,
    )
    assert val.is_valid is False
    assert val.status == "INDEPENDENT_VERIFICATION_FAILED"
    assert any("MUTUAL_EXCLUSIVITY_VIOLATION" in v for v in val.violations)


# ==============================================================================
# 3. PHYSICAL TSR MULTI-SEGMENT GEOMETRIC PARTITIONING
# ==============================================================================

def test_tsr_multi_segment_geometric_partitioning_no_double_counting():
    """Verify overlapping TSRs partition corridor geometry and pick minimum speed."""
    # Corridor 400 km to 440 km (40 km total) at normal 130 km/h
    # TSR A: 410 to 425 km @ 45 km/h
    # TSR B: 420 to 435 km @ 30 km/h
    # Overlap interval [420, 425] must resolve to 30 km/h (min speed) without double counting
    res = tsr_service.calculate_multi_tsr_runtime_dilation(
        corridor_start_km=400.0,
        corridor_end_km=440.0,
        normal_speed_kmph=130.0,
        tsrs=[
            {"start_km": 410.0, "end_km": 425.0, "restricted_speed_kmph": 45.0, "tsr_id": "TSR_A"},
            {"start_km": 420.0, "end_km": 435.0, "restricted_speed_kmph": 30.0, "tsr_id": "TSR_B"},
        ],
    )
    assert res["corridor_length_km"] == 40.0
    assert res["total_delay_minutes"] > 0.0

    segs = res["partitioned_segments"]
    # Boundaries: 400, 410, 420, 425, 435, 440 (5 disjoint segments)
    assert len(segs) == 5

    # Check the overlap segment [420.0, 425.0]
    overlap_seg = [s for s in segs if abs(s["start_km"] - 420.0) < 1e-3 and abs(s["end_km"] - 425.0) < 1e-3][0]
    assert overlap_seg["effective_speed_kmph"] == 30.0  # min(45, 30)

    # Check advisory disclaimer
    assert "CALCULATED_RUN_TIME_ONLY: DOES_NOT_CONSTITUTE_ENGINEERING_AUTHORIZATION_TO_LIFT_TSR" in res["disclaimer"]


def test_tsr_boundary_cases_and_error_handling():
    """Verify boundary conditions: zero-length segment, negative speed, and faster TSR."""
    # 1. Zero length segment
    zero_res = tsr_service.calculate_multi_tsr_runtime_dilation(
        corridor_start_km=400.0,
        corridor_end_km=400.0,
        normal_speed_kmph=130.0,
        tsrs=[],
    )
    assert zero_res["total_delay_minutes"] == 0.0

    # 2. Negative/zero speed raises ValueError
    with pytest.raises(ValueError, match="strictly positive"):
        tsr_service.calculate_multi_tsr_runtime_dilation(
            corridor_start_km=400.0,
            corridor_end_km=440.0,
            normal_speed_kmph=130.0,
            tsrs=[{"start_km": 410.0, "end_km": 420.0, "restricted_speed_kmph": -20.0}],
        )

    # 3. TSR speed higher than normal speed does not increase permitted speed
    fast_res = tsr_service.calculate_multi_tsr_runtime_dilation(
        corridor_start_km=400.0,
        corridor_end_km=440.0,
        normal_speed_kmph=110.0,
        tsrs=[{"start_km": 410.0, "end_km": 420.0, "restricted_speed_kmph": 160.0}],
    )
    assert fast_res["total_delay_minutes"] == 0.0


# ==============================================================================
# 4. TRANSACTIONAL SAFETY & CLEARANCE CONTROLS
# ==============================================================================

def test_separation_of_duties_prevents_creator_from_approving():
    """Verify that the user who initiated the block clearance cannot grant final approval."""
    block_id = "TEST-SOD-VIOLATION"
    clearance_service.create_clearance(
        ClearanceCreateRequest(
            block_id=block_id,
            section_id="KNP-PRYJ-SEC-B",
            duration_minutes=60,
            created_by="controller_akhil",
            initial_state=ClearanceStateEnum.AUTHORIZED,
        )
    )

    # Create active OHE permit so OHE gate passes
    traction_service.request_ohe_isolation(block_id=block_id)
    permit = traction_service.get_permit_for_block(block_id)
    traction_service.advance_ohe_state(permit.permit_id, TractionIsolationStateEnum.ISOLATION_PENDING, officer_id="TPC_1")
    traction_service.advance_ohe_state(permit.permit_id, TractionIsolationStateEnum.ISOLATION_CONFIRMED, officer_id="TPC_1")
    traction_service.advance_ohe_state(permit.permit_id, TractionIsolationStateEnum.EARTHING_CONFIRMED, officer_id="TPC_1")
    traction_service.advance_ohe_state(permit.permit_id, TractionIsolationStateEnum.PERMIT_ACTIVE, officer_id="TPC_1")

    # Creator attempts to approve their own block
    with pytest.raises(PermissionError, match="Separation of Duties Violation"):
        clearance_service.advance_clearance(
            block_id=block_id,
            request=ClearanceAdvanceRequest(
                target_state=ClearanceStateEnum.APPROVED,
                role=UserRoleEnum.SECTION_CONTROLLER,
                user_id="controller_akhil",
                comment="Self-approving my block",
            ),
        )


def test_revoked_ohe_permit_blocks_approval():
    """Verify that a revoked OHE permit blocks clearance approval."""
    block_id = "TEST-REVOKED-PERMIT"
    clearance_service.create_clearance(
        ClearanceCreateRequest(
            block_id=block_id,
            section_id="KNP-PRYJ-SEC-B",
            duration_minutes=60,
            created_by="ops_user_1",
            initial_state=ClearanceStateEnum.AUTHORIZED,
        )
    )

    # Issue and then REVOKE permit
    p = traction_service.request_ohe_isolation(block_id=block_id)
    traction_service.advance_ohe_state(p.permit_id, TractionIsolationStateEnum.ISOLATION_PENDING, officer_id="TPC_1")
    traction_service.advance_ohe_state(p.permit_id, TractionIsolationStateEnum.ISOLATION_CONFIRMED, officer_id="TPC_1")
    traction_service.advance_ohe_state(p.permit_id, TractionIsolationStateEnum.EARTHING_CONFIRMED, officer_id="TPC_1")
    traction_service.advance_ohe_state(p.permit_id, TractionIsolationStateEnum.PERMIT_ACTIVE, officer_id="TPC_1")
    # Revoke permit
    traction_service.advance_ohe_state(p.permit_id, TractionIsolationStateEnum.REVOKED, officer_id="TPC_1", remarks="Safety hazard detected")

    with pytest.raises(PermissionError, match="Traction Power Permit has been REVOKED"):
        clearance_service.advance_clearance(
            block_id=block_id,
            request=ClearanceAdvanceRequest(
                target_state=ClearanceStateEnum.APPROVED,
                role=UserRoleEnum.SECTION_CONTROLLER,
                user_id="independent_controller_9",
                comment="Approving block",
            ),
        )


def test_signaling_adapter_reports_not_connected():
    """Verify signaling adapter strictly declares NOT_CONNECTED non-vital status."""
    st = signaling_adapter.get_signaling_status()
    assert st["status"] == "NOT_CONNECTED"
    assert st["vital_interlocking_authorized"] is False
    assert st["signal_control_permitted"] is False
    assert "NON_VITAL_ADVISORY" in st["mode"]


# ==============================================================================
# 5. DATABASE DURABILITY & ONLINE BACKUP/RECOVERY
# ==============================================================================

def test_sqlite_online_backup_and_recovery_verification(tmp_path):
    """Verify SQLite zero-downtime online backup and test restore with hash validation."""
    success, backup_file, sha256_hash, counts = perform_sqlite_online_backup(dest_dir=tmp_path)
    assert success is True
    assert backup_file.exists()
    assert len(sha256_hash) == 64
    assert "users" in counts

    # Execute test restoration
    restored_target = tmp_path / "restored_verify.db"
    r_success, r_msg, r_counts = restore_sqlite_backup(backup_file, target_db_path=restored_target)
    assert r_success is True
    assert restored_target.exists()
    assert r_counts == counts
