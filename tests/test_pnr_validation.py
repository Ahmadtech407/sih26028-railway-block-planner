"""
Tests for Controlled Demo PNR Validation & Random PNR Rejection (SIH26028).
"""

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_pnr_ticket

client = TestClient(app)


def test_controlled_demo_pnr_verification():
    """Verify that the official controlled demo PNR returns the full demonstration ticket."""
    resp = client.post("/api/pnr/verify", json={"pnr": "8429103847"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["match_verified"] is True
    assert data["pnr"] == "8429103847"
    assert data["journey"]["train_number"] == "22436"
    assert data["journey"]["train_name"] == "Vande Bharat Express"
    assert "New Delhi" in data["journey"]["from_station"]
    assert "Jammu Tawi" in data["journey"]["to_station"]
    assert data["booking"]["coach"] == "C6"
    assert data["booking"]["seat_number"] == "46"
    assert data["booking"]["fare"] == 1480.00
    assert data["booking"]["status"] == "CNF"


def test_controlled_demo_pnr_alias():
    """Verify that alias demo PNR 8410000477 also returns the demonstration ticket."""
    resp = client.post("/api/pnr/verify", json={"pnr": "8410000477"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["booking"]["coach"] == "C6"
    assert data["booking"]["seat_number"] == "46"
    assert data["booking"]["fare"] == 1480.00


def test_random_pnr_returns_404_not_found():
    """Verify that a random PNR returns HTTP 404 and does NOT display demonstration data."""
    random_pnrs = ["9999999999", "1234567890", "0000000000", "9876543219"]
    for pnr in random_pnrs:
        resp = client.post("/api/pnr/verify", json={"pnr": pnr})
        assert resp.status_code == 404
        data = resp.json()
        assert data["success"] is False
        assert data["message"] == "PNR not found. Please check the PNR and try again."
        # Ensure demonstration data is NEVER leaked
        assert "booking" not in data
        assert "journey" not in data


def test_pnr_get_endpoint_valid_and_random():
    """Verify GET /api/pnr/{pnr} for valid demo PNR and random PNR."""
    resp_valid = client.get("/api/pnr/8429103847")
    assert resp_valid.status_code == 200
    assert resp_valid.json()["match_verified"] is True

    resp_random = client.get("/api/pnr/9999999999")
    assert resp_random.status_code == 404
    assert resp_random.json()["success"] is False
    assert resp_random.json()["message"] == "PNR not found. Please check the PNR and try again."


def test_tickets_verify_random_pnr_returns_404():
    """Verify /api/tickets/verify also returns 404 for random PNRs."""
    resp = client.post("/api/tickets/verify", json={"payload": "random-pnr-99999"})
    assert resp.status_code == 404
    assert resp.json()["success"] is False


def test_database_persistence_of_demo_tickets():
    """Verify that the demo ticket is stored in the database layer."""
    ticket = get_pnr_ticket("8429103847")
    assert ticket is not None
    assert ticket["pnr"] == "8429103847"
    assert ticket["booking"]["coach"] == "C6"
    assert ticket["booking"]["seat_number"] == "46"
    assert ticket["booking"]["fare"] == 1480.00
