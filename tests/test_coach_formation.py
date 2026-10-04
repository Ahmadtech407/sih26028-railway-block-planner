"""
Unit and integration tests for the Train Coach Position Feature (SIH26028).

Verifies:
1. Exact train-specific coach compositions from coach_formations.json.
2. findIndex() dynamic position calculation (no guessing, no hardcoding).
3. Relative section calculation (Front, Middle, Rear).
4. Correct count of passenger coaches before and after.
5. Verification status handling (VERIFIED, PARTIALLY_VERIFIED, UNAVAILABLE).
6. 404 behavior for unknown trains.
7. Unavailability notice behavior (never guess positions when data is absent).
"""

import json
import os
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

DATA_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "backend", "data", "coach_formations.json")
)


def test_coach_formations_json_exists():
    assert os.path.exists(DATA_PATH), f"File {DATA_PATH} must exist"
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "_meta" in data
    assert "formations" in data
    formations = data["formations"]
    assert "22436" in formations
    assert "12301" in formations
    assert "12004" in formations
    assert "12424" in formations


def test_train_22436_exact_b1_position():
    """Train 22436 (Vande Bharat): LOCO -> C1 -> C2 -> B1 -> B2 -> B3 -> A1. B1 is at index 3."""
    response = client.get("/api/trains/22436/formation")
    assert response.status_code == 200
    data = response.json()
    assert data["verificationStatus"] == "VERIFIED"
    assert data["trainNumber"] == "22436"

    coaches = data["coaches"]
    assert len(coaches) == 7

    # Use findIndex() dynamic search - never hardcoded
    b1_idx = next((i for i, c in enumerate(coaches) if c["coachId"] == "B1"), -1)
    assert b1_idx == 3, f"Expected B1 at index 3, got {b1_idx}"

    # Coaches before & after (excluding LOCO)
    passengers_before = sum(1 for c in coaches[:b1_idx] if c["type"] != "LOCOMOTIVE")
    passengers_after = sum(1 for c in coaches[b1_idx + 1:] if c["type"] != "LOCOMOTIVE")
    assert passengers_before == 2  # C1, C2
    assert passengers_after == 3   # B2, B3, A1

    # Ratio calculation
    ratio = b1_idx / (len(coaches) - 1)
    assert 0.33 < ratio <= 0.66  # Middle section (3/6 = 0.50)


def test_train_12301_different_b1_position():
    """Train 12301 (Rajdhani): LOCO -> S1 -> S2 -> A1 -> A2 -> B1 -> B2 -> B3 -> LOCO. B1 is at index 5."""
    response = client.get("/api/trains/12301/formation")
    assert response.status_code == 200
    data = response.json()
    assert data["verificationStatus"] == "VERIFIED"

    coaches = data["coaches"]
    assert len(coaches) == 9

    b1_idx = next((i for i, c in enumerate(coaches) if c["coachId"] == "B1"), -1)
    assert b1_idx == 5, f"Expected B1 at index 5, got {b1_idx}"

    passengers_before = sum(1 for c in coaches[:b1_idx] if c["type"] != "LOCOMOTIVE")
    passengers_after = sum(1 for c in coaches[b1_idx + 1:] if c["type"] != "LOCOMOTIVE")
    assert passengers_before == 4  # S1, S2, A1, A2
    assert passengers_after == 2   # B2, B3


def test_train_12004_partially_verified():
    """Train 12004 (Shatabdi): Status must be PARTIALLY_VERIFIED."""
    response = client.get("/api/trains/12004/formation")
    assert response.status_code == 200
    data = response.json()
    assert data["verificationStatus"] == "PARTIALLY_VERIFIED"
    assert len(data["coaches"]) == 7


def test_train_12424_unavailable_never_guesses():
    """Train 12424: Formation must be UNAVAILABLE with empty coaches array - no guessing."""
    response = client.get("/api/trains/12424/formation")
    assert response.status_code == 200
    data = response.json()
    assert data["verificationStatus"] == "UNAVAILABLE"
    assert data["coaches"] == []


def test_unknown_train_returns_404():
    """Unknown train returns 404 with clear message."""
    response = client.get("/api/trains/99999/formation")
    assert response.status_code == 404
    assert "currently unavailable" in response.json()["detail"]
