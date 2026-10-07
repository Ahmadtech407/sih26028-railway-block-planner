"""
Automated Security & Privacy Test Suite for RailTrack (SIH26028).

Validates the 12 critical production security boundaries:
1. Anonymous user cannot obtain passenger coach/seat information.
2. Anonymous user cannot call coach-position API by supplying arbitrary coach/seat values.
3. Invalid PNR format cannot reveal passenger information.
4. Fake 10-digit PNR cannot be treated as verified.
5. Successful verified PNR returns authentic passenger journey data.
6. Frontend cannot override verified coach.
7. Frontend cannot override verified seat.
8. Clearing verified session removes passenger-specific information.
9. Formation is not exposed as passenger-specific information before verification.
10. Unknown formation returns UNAVAILABLE instead of guessed data.
11. Verified static formation is correctly labelled VERIFIED_STATIC.
12. Live formation is labelled LIVE only when an actual verified live source is used.
"""

import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.ticket_service import KNOWN_TICKETS

client = TestClient(app)


# --------------------------------------------------------------------------
# TEST 1: Anonymous user cannot obtain passenger coach/seat information
# --------------------------------------------------------------------------
def test_1_anonymous_user_cannot_obtain_passenger_coach_seat():
    """Anonymous requests without a session token are strictly rejected with 401."""
    res = client.post("/api/pnr/coach-position", json={"session_token": ""})
    assert res.status_code == 401
    assert "Authentication required" in res.json().get("detail", "")
    assert "coach" not in res.json()
    assert "seat" not in res.json()


# --------------------------------------------------------------------------
# TEST 2: Arbitrary coach/seat parameter injection is rejected
# --------------------------------------------------------------------------
def test_2_arbitrary_coach_seat_parameter_injection_rejected():
    """Unauthenticated client cannot pass arbitrary coach/seat to obtain positioning."""
    malicious_payload = {
        "session_token": "invalid_or_forged_token_12345",
        "coach": "GS1",
        "seat": "36",
    }
    res = client.post("/api/pnr/coach-position", json=malicious_payload)
    assert res.status_code == 401
    assert res.json().get("status") == "UNAUTHORIZED"


# --------------------------------------------------------------------------
# TEST 3: Invalid PNR format cannot reveal passenger information
# --------------------------------------------------------------------------
def test_3_invalid_pnr_format_rejected():
    """PNRs that are not exactly 10 digits are rejected with 400 Bad Request."""
    invalid_cases = ["", "12345", "ABC1234567", "12345678901", "123-456-78"]
    for bad_pnr in invalid_cases:
        res = client.post("/api/pnr/verify", json={"pnr": bad_pnr})
        assert res.status_code == 400
        assert "valid 10-digit PNR" in res.json().get("detail", "")
        assert "journey" not in res.json()


# --------------------------------------------------------------------------
# TEST 4: Fake 10-digit PNR cannot be treated as verified
# --------------------------------------------------------------------------
def test_4_fake_10_digit_pnr_rejected():
    """A valid 10-digit format is not proof of booking; nonexistent PNRs return 404."""
    fake_pnrs = ["9999999999", "0000000000", "1112223334", "7896541230"]
    for fake in fake_pnrs:
        res = client.post("/api/pnr/verify", json={"pnr": fake})
        assert res.status_code == 404
        assert "could not be verified" in res.json().get("detail", "")
        assert "session_token" not in res.json()


# --------------------------------------------------------------------------
# TEST 5: Successful verified PNR returns correct passenger journey data
# --------------------------------------------------------------------------
def test_5_real_verified_pnr_returns_authentic_journey_data():
    """Verified PNR returns authentic train, coach, seat, and short-lived session token."""
    res = client.post("/api/pnr/verify", json={"pnr": "1234567890"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "session_token" in data and len(data["session_token"]) >= 32
    journey = data["journey"]
    assert journey["train_number"] == "12802"
    assert "Purushottam" in journey["train_name"]
    assert journey["coach"] == "GS1"
    assert journey["seat_number"] == "36"
    assert journey["from_station"] == "New Delhi (NDLS)"
    assert journey["to_station"] == "Puri (PURI)"


# --------------------------------------------------------------------------
# TEST 6: Frontend cannot override verified coach
# --------------------------------------------------------------------------
def test_6_frontend_cannot_override_verified_coach():
    """Server derives coach strictly from verified session; client overrides are ignored."""
    v_res = client.post("/api/pnr/verify", json={"pnr": "1234567890"})
    assert v_res.status_code == 200
    token = v_res.json()["session_token"]

    # Client attempts to spoof coach as "H1"
    tampered_payload = {
        "session_token": token,
        "coach": "H1",
    }
    pos_res = client.post("/api/pnr/coach-position", json=tampered_payload)
    assert pos_res.status_code == 200
    pos_data = pos_res.json()
    # Coach MUST remain GS1 (derived strictly from server session)
    assert pos_data["coach"] == "GS1"
    assert pos_data["position"] == 3  # Position 3 of 22 in Train 12802


# --------------------------------------------------------------------------
# TEST 7: Frontend cannot override verified seat
# --------------------------------------------------------------------------
def test_7_frontend_cannot_override_verified_seat():
    """Server derives seat strictly from verified session; client overrides are ignored."""
    v_res = client.post("/api/pnr/verify", json={"pnr": "1234567890"})
    assert v_res.status_code == 200
    token = v_res.json()["session_token"]

    # Client attempts to spoof seat as "99A"
    tampered_payload = {
        "session_token": token,
        "seat": "99A",
    }
    pos_res = client.post("/api/pnr/coach-position", json=tampered_payload)
    assert pos_res.status_code == 200
    pos_data = pos_res.json()
    # Seat MUST remain 36
    assert pos_data["seat"] == "36"


# --------------------------------------------------------------------------
# TEST 8: Clearing verified session removes passenger-specific information
# --------------------------------------------------------------------------
def test_8_clearing_session_removes_passenger_data():
    """Logging out / clearing session immediately revokes access to coach positioning."""
    v_res = client.post("/api/pnr/verify", json={"pnr": "1234567890"})
    assert v_res.status_code == 200
    token = v_res.json()["session_token"]

    pre_clear = client.post("/api/pnr/coach-position", json={"session_token": token})
    assert pre_clear.status_code == 200

    logout_res = client.post("/api/pnr/logout", json={"session_token": token})
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    post_clear = client.post("/api/pnr/coach-position", json={"session_token": token})
    assert post_clear.status_code == 401


# --------------------------------------------------------------------------
# TEST 9: Formation is not exposed as passenger-specific before verification
# --------------------------------------------------------------------------
def test_9_formation_not_exposed_as_passenger_specific_before_verification():
    """Unauthenticated requests cannot receive personalized coach highlight markers."""
    res = client.post("/api/pnr/coach-position", json={"session_token": "anonymous_guest"})
    assert res.status_code == 401
    assert "position" not in res.json()
    assert "coaches" not in res.json()


# --------------------------------------------------------------------------
# TEST 10: Unknown formation returns UNAVAILABLE instead of guessed data
# --------------------------------------------------------------------------
def test_10_unknown_formation_returns_unavailable():
    """If train formation is not in database, system returns UNAVAILABLE (never guesses)."""
    from backend.database import create_pnr_session
    import secrets
    from datetime import datetime, timezone, timedelta

    token = secrets.token_hex(32)
    exp = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    create_pnr_session(
        token=token,
        pnr="9998887776",
        journey_data={
            "train_number": "99999",
            "train_name": "Test Special",
            "coach": "S1",
            "seat_number": "20",
        },
        expires_at_iso=exp,
    )

    res = client.post("/api/pnr/coach-position", json={"session_token": token})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "UNAVAILABLE"
    assert data["provenance"] == "UNAVAILABLE"
    assert "verified coach formation is currently unavailable" in data["message"]


# --------------------------------------------------------------------------
# TEST 11: Verified static formation is correctly labelled VERIFIED_STATIC
# --------------------------------------------------------------------------
def test_11_verified_static_formation_labelled_verified_static():
    """Authentic timetabled formations are explicitly tagged VERIFIED_STATIC."""
    v_res = client.post("/api/pnr/verify", json={"pnr": "1234567890"})
    token = v_res.json()["session_token"]

    pos_res = client.post("/api/pnr/coach-position", json={"session_token": token})
    assert pos_res.status_code == 200
    data = pos_res.json()
    assert data["status"] == "SUCCESS"
    assert data["provenance"] == "VERIFIED_STATIC"
    assert data["position"] == 3
    assert data["section"] == "Front Section"
    assert data["coaches_before"] == 2
    assert data["coaches_after"] == 19


# --------------------------------------------------------------------------
# TEST 12: Live formation is labelled LIVE only when live source is active
# --------------------------------------------------------------------------
def test_12_live_formation_labelled_live_only_when_live_source_active():
    """Static formation lookups NEVER return 'LIVE' unless an active telemetry source confirms it."""
    v_res = client.post("/api/pnr/verify", json={"pnr": "8429103847"})
    token = v_res.json()["session_token"]

    pos_res = client.post("/api/pnr/coach-position", json={"session_token": token})
    assert pos_res.status_code == 200
    data = pos_res.json()
    assert data["provenance"] != "LIVE"
    assert data["provenance"] == "VERIFIED_STATIC"
