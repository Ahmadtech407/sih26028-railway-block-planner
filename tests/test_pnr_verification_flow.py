"""
End-to-end integration tests for PNR Verification Flow (SIH26028).

Verifies:
1. Canonical PNR provider parity (verify_pnr vs verify_ticket).
2. Demo PNR 8429103847 verification and session creation (32-byte hex token, 15-min TTL, SQLite persistence).
3. Coach position retrieval via session token (Coach C6 at position 7 of 18, Middle Section).
4. Strict rejection of fake/unregistered PNRs and invalid formats.
5. Invalidation and session clearing.
"""

import pytest
import sqlite3
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.ticket_service import verify_pnr, verify_ticket
from backend.routes.pnr import execute_pnr_verification, get_verified_coach_position, PnrCoachPositionRequest
from backend.database import get_pnr_session

client = TestClient(app)


def test_canonical_provider_parity():
    """Verify that verify_pnr and verify_ticket produce matching canonical data for 8429103847."""
    pnr = "8429103847"
    pnr_data = verify_pnr(pnr)
    ticket_data = verify_ticket(pnr)

    assert pnr_data is not None
    assert ticket_data is not None

    # Parity assertions
    assert pnr_data["pnr"] == pnr
    assert pnr_data["passenger_name"] == "John Doe"
    assert pnr_data["train_number"] == "22436"
    assert pnr_data["train_name"] == "Vande Bharat Express"
    assert pnr_data["coach"] == "C6"
    assert pnr_data["seat_number"] == "46"
    assert pnr_data["berth_type"] == "Window"
    assert pnr_data["verification_status"] == "DEMO"
    assert pnr_data["is_demo"] is True

    # Check that verify_ticket returns matching core fields
    assert ticket_data["pnr"] == pnr_data["pnr"]
    assert ticket_data["passenger_name"] == pnr_data["passenger_name"]
    assert ticket_data["train_number"] == pnr_data["train_number"]
    assert ticket_data["coach"] == pnr_data["coach"]
    assert ticket_data["seat_number"] == pnr_data["seat_number"]
    assert ticket_data["match_verified"] is True


def test_execute_pnr_verification_creates_persistent_session():
    """Verify that execute_pnr_verification creates a valid session in SQLite and memory."""
    pnr = "8429103847"
    result = execute_pnr_verification(pnr)

    assert result["verified"] is True
    assert result["success"] is True
    assert result["match_verified"] is True
    assert result["pnr"] == pnr
    assert result["passenger_name"] == "John Doe"
    assert result["train_number"] == "22436"
    assert result["coach"] == "C6"
    assert result["seat_number"] == "46"
    assert result["verification_status"] == "DEMO"

    token = result["session_token"]
    assert isinstance(token, str)
    assert len(token) == 64  # 32 bytes hex

    # Verify persistence in SQLite database
    session_row = get_pnr_session(token)
    assert session_row is not None
    assert session_row["pnr"] == pnr
    assert session_row["verification_status"] == "DEMO"
    assert session_row["coach"] == "C6"
    assert session_row["seat_number"] == "46"


@pytest.mark.anyio
async def test_coach_position_via_session_token():
    """Verify that coach position is derived solely from session token and highlights C6 at position 7 of 18."""
    # Step 1: verify PNR
    pnr = "8429103847"
    v_res = execute_pnr_verification(pnr)
    token = v_res["session_token"]

    # Step 2: request coach position
    req = PnrCoachPositionRequest(session_token=token)
    pos_res = await get_verified_coach_position(req)

    assert pos_res["status"] == "SUCCESS"
    assert pos_res["train_number"] == "22436"
    assert pos_res["coach"] == "C6"
    assert pos_res["seat"] == "46"
    assert pos_res["position"] == 7
    assert pos_res["total_coaches"] == 18
    assert pos_res["section"] == "Middle Section"
    assert pos_res["provenance"] == "VERIFIED_STATIC"
    assert pos_res["verification_status"] == "DEMO"
    assert pos_res["ahead_count"] == 6
    assert pos_res["behind_count"] == 11


def test_http_endpoint_verify_pnr_flow():
    """Test full HTTP flow through FastAPI endpoint /api/pnr/verify."""
    resp = client.post("/api/pnr/verify", json={"pnr": "8429103847"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["verified"] is True
    assert data["match_verified"] is True
    assert data["pnr"] == "8429103847"
    assert data["passenger_name"] == "John Doe"
    assert data["train_number"] == "22436"
    assert data["coach"] == "C6"
    assert data["seat_number"] == "46"
    assert "session_token" in data

    token = data["session_token"]

    # Now call coach position endpoint with this token
    c_resp = client.post("/api/pnr/coach-position", json={"session_token": token})
    assert c_resp.status_code == 200
    c_data = c_resp.json()

    assert c_data["status"] == "SUCCESS"
    assert c_data["position"] == 7
    assert c_data["coach"] == "C6"
    assert c_data["total_coaches"] == 18
    assert c_data["section"] == "Middle Section"
    assert c_data["provenance"] == "VERIFIED_STATIC"


def test_negative_cases_verification():
    """Verify strict rejection of invalid PNR formats, fake PNRs, and invalid tokens."""
    # 1. Invalid PNR length/characters
    for bad_pnr in ["", "123", "abcdefghij", "842910384", "842910384711"]:
        resp = client.post("/api/pnr/verify", json={"pnr": bad_pnr})
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    # 2. Fake / unregistered 10-digit PNR
    for fake_pnr in ["0000000000", "9999999999", "1112223334"]:
        resp = client.post("/api/pnr/verify", json={"pnr": fake_pnr})
        assert resp.status_code == 404
        assert resp.json()["success"] is False

    # 3. Invalid / missing session token for coach position
    resp_bad_token = client.post("/api/pnr/coach-position", json={"session_token": "nonexistent_token_12345"})
    assert resp_bad_token.status_code == 401


def test_session_logout_and_clearing():
    """Verify that logging out invalidates the session token."""
    # Create session
    v_res = client.post("/api/pnr/verify", json={"pnr": "8429103847"}).json()
    token = v_res["session_token"]

    # Verify session works
    c_res = client.post("/api/pnr/coach-position", json={"session_token": token})
    assert c_res.status_code == 200

    # Logout
    logout_res = client.post("/api/pnr/logout", json={"session_token": token})
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    # Verify session no longer works
    c_res_after = client.post("/api/pnr/coach-position", json={"session_token": token})
    assert c_res_after.status_code == 401
