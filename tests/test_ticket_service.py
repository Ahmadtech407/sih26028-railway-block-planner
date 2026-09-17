"""
Tests for Ticket Verification Service & API Endpoints (SIH26028).
"""

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.ticket_service import verify_ticket, sanitize_payload


client = TestClient(app)


def test_sanitize_payload_variants():
    assert sanitize_payload("8429103847") == "8429103847"
    assert sanitize_payload("PNR-8429103847") == "8429103847"
    assert sanitize_payload("pnr: 8429103847 ") == "8429103847"
    assert sanitize_payload('{"pnr": "2840192841"}') == "2840192841"


def test_known_ticket_verification():
    result = verify_ticket("8429103847")
    assert result["status"] == "SUCCESS"
    assert result["match_verified"] is True
    assert result["passenger"]["name"] == "John Doe"
    assert result["journey"]["train_number"] == "22436"
    assert result["booking"]["coach"] in ("C6", "C4")
    assert result["booking"]["seat_number"] in ("46", "28")
    assert result["booking"]["status"] == "CNF"


def test_ticket_verification_by_prefixed_pnr():
    result = verify_ticket("PNR-2840192841")
    assert result["status"] == "SUCCESS"
    assert result["match_verified"] is True
    assert result["passenger"]["name"] == "Priya Sharma"
    assert result["journey"]["train_number"] == "12302"
    assert result["booking"]["coach"] == "B2"


def test_random_pnr_rejected_without_synthesis():
    result = verify_ticket("4598127391")
    assert result["match_verified"] is False
    assert result["status"] == "NOT_FOUND"
    assert "PNR not found" in result["message"]


def test_empty_payload_verification():
    result = verify_ticket("")
    assert result["match_verified"] is False
    assert result["status"] == "ERROR"


def test_ticket_api_get_endpoint():
    resp = client.get("/api/tickets/8429103847")
    assert resp.status_code == 200
    data = resp.json()
    assert data["match_verified"] is True
    assert data["passenger"]["name"] == "John Doe"
    assert data["journey"]["train_number"] == "22436"


def test_ticket_api_post_verify_endpoint():
    resp = client.post("/api/tickets/verify", json={"payload": "PNR-9812401823"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["match_verified"] is True
    assert data["passenger"]["name"] == "Amit Patel"
    assert data["journey"]["train_number"] == "12802"
