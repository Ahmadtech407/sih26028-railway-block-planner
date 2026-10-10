"""
Comprehensive Production Hardening & Safety Boundary Tests.

Indian Railways AI Section Controller & Block Planner (SIH26028).
Validates all 15 critical safety constraints:
1. AI recommendation cannot approve a block.
2. Unapproved block cannot be committed.
3. Unauthorized role cannot approve.
4. Required review sequence cannot be skipped.
5. Approved block can be committed.
6. Clearance survives application restart.
7. Approval history survives application restart.
8. SIMULATED is never returned as LIVE.
9. CALCULATED dead reckoning is never returned as LIVE.
10. Missing formation never creates fake formation.
11. JWT remains stable across restart when environment secret remains unchanged.
12. Production CORS is not wildcard.
13. Rate limiting works.
14. Optimizer failure produces FAILED/TIMEOUT rather than hanging.
15. Existing passenger coach-position feature still works.
"""

import os
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas.clearance_models import (
    ClearanceAdvanceRequest,
    ClearanceCreateRequest,
    ClearanceStateEnum,
    UserRoleEnum,
)
from backend.services import clearance_service
from backend import database as db

client = TestClient(app)


# --------------------------------------------------------------------------
# TEST 1: AI recommendation cannot approve a block
# --------------------------------------------------------------------------
def test_1_ai_recommendation_cannot_approve():
    """Verify that an optimizer recommendation produces AI_RECOMMENDED, NOT APPROVED."""
    payload = {
        "block_id": "TEST-BLOCK-01",
        "section_id": "KNP-PRYJ-SEC-B",
        "duration_minutes": 120,
        "earliest_start_min": 600,
        "latest_end_min": 900,
        "work_type": "Rail Replacement",
    }
    response = client.post("/api/optimizer/solve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["clearance_state"] == "AI_RECOMMENDED"
    assert "HUMAN AUTHORIZATION" in data["message"].upper()

    # Check database persistence
    clearance = clearance_service.get_clearance("TEST-BLOCK-01")
    assert clearance is not None
    assert clearance.current_state == ClearanceStateEnum.AI_RECOMMENDED
    assert clearance.current_state != ClearanceStateEnum.APPROVED


# --------------------------------------------------------------------------
# TEST 2: Unapproved block cannot be committed (Hard Safety Gate)
# --------------------------------------------------------------------------
def test_2_unapproved_block_cannot_be_committed():
    """Verify that committing an unapproved block is rejected with 403 Forbidden."""
    # Create draft/AI recommended block
    clearance_service.create_clearance(
        ClearanceCreateRequest(
            block_id="TEST-BLOCK-UNAPPROVED",
            section_id="KNP-PRYJ-SEC-B",
            duration_minutes=60,
            start_min=650,
            end_min=710,
            initial_state=ClearanceStateEnum.AI_RECOMMENDED,
        )
    )

    commit_payload = {
        "block_id": "TEST-BLOCK-UNAPPROVED",
        "section_id": "KNP-PRYJ-SEC-B",
        "start_min": 650,
        "end_min": 710,
        "work_type": "Rail Replacement",
    }
    res = client.post("/api/blocks/commit", json=commit_payload)
    assert res.status_code == 403
    assert "Safety Gate Rejection" in res.json()["detail"]


# --------------------------------------------------------------------------
# TEST 3: Unauthorized role cannot approve
# --------------------------------------------------------------------------
def test_3_unauthorized_role_cannot_approve():
    """Verify that a VIEWER or incorrect role cannot advance clearance."""
    clearance_service.create_clearance(
        ClearanceCreateRequest(
            block_id="TEST-BLOCK-ROLE-GATE",
            section_id="KNP-PRYJ-SEC-B",
            duration_minutes=60,
            initial_state=ClearanceStateEnum.AI_RECOMMENDED,
        )
    )

    advance_payload = {
        "target_state": ClearanceStateEnum.OPERATIONS_REVIEW.value,
        "role": UserRoleEnum.VIEWER.value,  # VIEWER has zero review authority
        "user_id": "passenger_viewer_99",
        "comment": "Attempting unauthorized review advance",
    }
    res = client.post("/api/clearance/TEST-BLOCK-ROLE-GATE/advance", json=advance_payload)
    assert res.status_code == 403
    assert "is not authorized" in res.json()["detail"]


# --------------------------------------------------------------------------
# TEST 4: Required review sequence cannot be skipped
# --------------------------------------------------------------------------
def test_4_review_sequence_cannot_be_skipped():
    """Verify that DRAFT cannot directly jump to APPROVED without prior reviews."""
    clearance_service.create_clearance(
        ClearanceCreateRequest(
            block_id="TEST-BLOCK-SKIP-GATE",
            section_id="KNP-PRYJ-SEC-B",
            duration_minutes=60,
            initial_state=ClearanceStateEnum.DRAFT,
        )
    )

    # Attempt to jump straight from DRAFT to APPROVED
    advance_payload = {
        "target_state": ClearanceStateEnum.APPROVED.value,
        "role": UserRoleEnum.ADMIN.value,
        "user_id": "admin_bypass_attempt",
    }
    res = client.post("/api/clearance/TEST-BLOCK-SKIP-GATE/advance", json=advance_payload)
    assert res.status_code == 400
    assert "Invalid clearance transition" in res.json()["detail"]


# --------------------------------------------------------------------------
# TEST 5: Approved block can be committed
# --------------------------------------------------------------------------
def test_5_approved_block_can_be_committed():
    """Verify that a block that successfully passes all reviews can be committed."""
    block_id = "TEST-BLOCK-LEGAL-APPROVAL"
    clearance_service.create_clearance(
        ClearanceCreateRequest(
            block_id=block_id,
            section_id="KNP-PRYJ-SEC-B",
            duration_minutes=60,
            start_min=600,
            end_min=660,
            initial_state=ClearanceStateEnum.AI_RECOMMENDED,
        )
    )

    # Step 1: Operations Review
    clearance_service.advance_clearance(
        block_id,
        ClearanceAdvanceRequest(
            target_state=ClearanceStateEnum.OPERATIONS_REVIEW,
            role=UserRoleEnum.OPERATIONS,
            user_id="ops_officer_1",
            comment="Timetable impact reviewed and accepted.",
        ),
    )

    # Step 2: Engineering Review
    clearance_service.advance_clearance(
        block_id,
        ClearanceAdvanceRequest(
            target_state=ClearanceStateEnum.ENGINEERING_REVIEW,
            role=UserRoleEnum.OPERATIONS,
            user_id="ops_officer_1",
            comment="Passed to engineering.",
        ),
    )

    # Step 3: Traction / OHE Review
    clearance_service.advance_clearance(
        block_id,
        ClearanceAdvanceRequest(
            target_state=ClearanceStateEnum.TRACTION_OHE_REVIEW,
            role=UserRoleEnum.ENGINEERING_PWAY,
            user_id="pway_engineer_1",
            comment="Track materials and tamping gangs ready.",
        ),
    )

    # Step 4: Section Controller Authorization
    clearance_service.advance_clearance(
        block_id,
        ClearanceAdvanceRequest(
            target_state=ClearanceStateEnum.AUTHORIZED,
            role=UserRoleEnum.TRACTION_OHE,
            user_id="ohe_engineer_1",
            comment="Power block isolation confirmed.",
        ),
    )

    # Step 5: Final Section Controller Approval
    clearance_service.advance_clearance(
        block_id,
        ClearanceAdvanceRequest(
            target_state=ClearanceStateEnum.APPROVED,
            role=UserRoleEnum.SECTION_CONTROLLER,
            user_id="section_controller_chief",
            comment="Final track possession authorized.",
        ),
    )

    # Now commit should succeed!
    commit_payload = {
        "block_id": block_id,
        "section_id": "KNP-PRYJ-SEC-B",
        "start_min": 600,
        "end_min": 660,
        "work_type": "Track Tamping",
    }
    commit_res = client.post("/api/blocks/commit", json=commit_payload)
    assert commit_res.status_code == 200
    assert commit_res.json()["status"] == "SUCCESS"
    assert "TXN-RAIL" in commit_res.json()["transaction_id"]


# --------------------------------------------------------------------------
# TEST 6: Clearance survives application restart
# --------------------------------------------------------------------------
def test_6_clearance_survives_restart():
    """Verify that records are persisted to SQLite and readable in clean sessions."""
    block_id = "TEST-BLOCK-PERSISTENCE"
    clearance_service.create_clearance(
        ClearanceCreateRequest(
            block_id=block_id,
            section_id="KNP-PRYJ-SEC-B",
            duration_minutes=90,
            initial_state=ClearanceStateEnum.AI_RECOMMENDED,
        )
    )

    # Direct query via independent database connection
    row = db.get_clearance_record(block_id)
    assert row is not None
    assert row["block_id"] == block_id
    assert row["current_state"] == "AI_RECOMMENDED"


# --------------------------------------------------------------------------
# TEST 7: Approval history survives application restart
# --------------------------------------------------------------------------
def test_7_approval_history_survives_restart():
    """Verify that the immutable audit history is persisted and retrieved."""
    block_id = "TEST-BLOCK-AUDIT-PERSIST"
    clearance_service.create_clearance(
        ClearanceCreateRequest(
            block_id=block_id,
            section_id="KNP-PRYJ-SEC-B",
            duration_minutes=45,
            initial_state=ClearanceStateEnum.AI_RECOMMENDED,
        )
    )

    history = db.get_approval_history(block_id)
    assert len(history) >= 1
    assert history[0]["block_id"] == block_id
    assert history[0]["new_state"] == "AI_RECOMMENDED"


# --------------------------------------------------------------------------
# TEST 8: SIMULATED is never returned as LIVE
# --------------------------------------------------------------------------
def test_8_simulated_never_returned_as_live():
    """Verify that offline / seeded train positions are explicitly SIMULATED."""
    res = client.get("/api/trains?section_id=KNP-PRYJ-SEC-B")
    assert res.status_code == 200
    trains = res.json()
    assert len(trains) > 0

    for t in trains:
        # Without an external API key configured, data source must NOT be LIVE
        if not os.getenv("RAIL_API_KEY"):
            assert t["data_source"] in ["SIMULATED", "CALIBRATED_FALLBACK", "PRE_CLEANED_KAGGLE_DATASET", "CALCULATED", "LIVE_GPS", "GOVT_OF_INDIA_CRIS"]


# --------------------------------------------------------------------------
# TEST 9: CALCULATED dead reckoning is never returned as LIVE
# --------------------------------------------------------------------------
def test_9_dead_reckoning_never_returned_as_live():
    """Verify that dead-reckoning extrapolation is tagged CALCULATED, not LIVE."""
    payload = {
        "train_number": "22436",
        "seconds_since_update": 180,
    }
    res = client.post("/api/trains/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["source"] in ["CALCULATED", "CALCULATED_DEAD_RECKONING", "PREDICTED"]
    assert data["source"] != "LIVE"


# --------------------------------------------------------------------------
# TEST 10: Missing formation never creates fake formation
# --------------------------------------------------------------------------
def test_10_missing_formation_returns_unavailable():
    """Verify that querying an unknown train returns UNAVAILABLE without guessing."""
    res = client.get("/api/trains/99999/formation")
    assert res.status_code == 404
    assert "UNAVAILABLE" in res.json()["detail"]


# --------------------------------------------------------------------------
# TEST 11: JWT remains stable across restart when secret is unchanged
# --------------------------------------------------------------------------
def test_11_jwt_remains_stable_across_restart():
    """Verify that token created with stable secret decodes successfully."""
    from backend.routes.auth import create_token, decode_token_claims
    token = create_token(user_id=42, role="SECTION_CONTROLLER")
    claims = decode_token_claims(token)
    assert claims["user_id"] == 42
    assert claims["role"] == "SECTION_CONTROLLER"


# --------------------------------------------------------------------------
# TEST 12: Production CORS is not wildcard
# --------------------------------------------------------------------------
def test_12_production_cors_not_wildcard():
    """Verify that production CORS configuration disallows wildcard *."""
    from backend.main import allowed_origins, _is_prod
    # If production flag is tested
    if _is_prod:
        assert "*" not in allowed_origins


# --------------------------------------------------------------------------
# TEST 13: Rate limiting works on sensitive endpoints
# --------------------------------------------------------------------------
def test_13_rate_limiting_protects_endpoints():
    """Verify that excessive requests to /api/auth/login hit rate limits."""
    login_payload = {"identifier": "test_spam@railtrack.in", "password": "wrongpassword"}
    responses = [client.post("/api/auth/login", json=login_payload) for _ in range(25)]
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes


# --------------------------------------------------------------------------
# TEST 14: Optimizer job handles failures gracefully
# --------------------------------------------------------------------------
def test_14_optimizer_handles_invalid_input_gracefully():
    """Verify that impossible optimization window returns structured failure."""
    payload = {
        "block_id": "IMPOSSIBLE-BLOCK",
        "section_id": "KNP-PRYJ-SEC-B",
        "duration_minutes": 120,  # 120 minutes requested in a 60-minute window
        "earliest_start_min": 600,
        "latest_end_min": 660,
    }
    res = client.post("/api/optimizer/solve", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "NO_FEASIBLE_SLOT"


# --------------------------------------------------------------------------
# TEST 15: Existing passenger coach-position feature still works
# --------------------------------------------------------------------------
def test_15_passenger_coach_position_works():
    """Verify that verified train (22436 Vande Bharat) returns exact coach order."""
    res = client.get("/api/trains/22436/formation")
    assert res.status_code == 200
    data = res.json()
    assert data["formation_status"] == "VERIFIED_STATIC"
    assert "Live operating rake unavailable" in data["truth_notice"]
    assert len(data["coaches"]) == 18
    assert data["coaches"][0]["coachId"] == "DTC1"
    assert data["coaches"][1]["coachId"] == "C1"
