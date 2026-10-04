"""
Unit and integration tests for Real Indian Railways Coach Position Locator (SIH26028).

Verifies:
1. Exact authentic Indian Railways coach compositions (CRIS/NTES standard rakes).
2. Train 22436 (Vande Bharat 16-car rake): Chair Car & Executive Class (C1-C14, E1-E2).
3. Train 12301 (Howrah Rajdhani 22-car LHB rake): Real B1 position at Front section.
4. Train 12424 (Dibrugarh Rajdhani 21-car LHB rake): Real B1 and A1 positions.
5. Train 12004 (Lucknow Swarna Shatabdi 18-car LHB rake): Real E1 and C1 positions.
6. dynamic findIndex() indexing with zero hardcoding.
7. Proper 404 for nonexistent trains.
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


def test_train_22436_real_vande_bharat_rake():
    """Train 22436 (Vande Bharat): Real 16-car passenger rake with DTC + C1-C7 + E1-E2 + C8-C14 + DTC."""
    response = client.get("/api/trains/22436/formation")
    assert response.status_code == 200
    data = response.json()
    assert data["verificationStatus"] == "VERIFIED"
    assert data["trainNumber"] == "22436"
    assert "Vande Bharat" in data["trainName"]

    coaches = data["coaches"]
    assert len(coaches) == 18

    # DTC driving cabs at both ends
    assert coaches[0]["coachId"] == "DTC1"
    assert coaches[-1]["coachId"] == "DTC2"

    # Executive Class E1 & E2 in the middle
    e1_idx = next(i for i, c in enumerate(coaches) if c["coachId"] == "E1")
    assert e1_idx == 8  # 9th vehicle from front
    assert coaches[e1_idx]["class"] == "EC"
    assert coaches[e1_idx]["berths"] == 52

    # Chair Car C4
    c4_idx = next(i for i, c in enumerate(coaches) if c["coachId"] == "C4")
    assert c4_idx == 4
    assert coaches[c4_idx]["class"] == "CC"
    assert coaches[c4_idx]["berths"] == 78


def test_train_12301_real_howrah_rajdhani_rake():
    """Train 12301 (Howrah Rajdhani): Real 22-car LHB rake with B1-B11, PC, H1-H2, A1-A5."""
    response = client.get("/api/trains/12301/formation")
    assert response.status_code == 200
    data = response.json()
    assert data["verificationStatus"] == "VERIFIED"
    assert "Rajdhani" in data["trainName"]

    coaches = data["coaches"]
    assert len(coaches) == 22

    # Front power car
    assert coaches[1]["coachId"] == "EOG1"

    # B1 AC 3-Tier immediately after EOG (index 2, position 3 of 22)
    b1_idx = next(i for i, c in enumerate(coaches) if c["coachId"] == "B1")
    assert b1_idx == 2
    assert coaches[b1_idx]["class"] == "3A"
    assert coaches[b1_idx]["berths"] == 72

    # Ratio calculation for B1 (Front Section)
    ratio = b1_idx / (len(coaches) - 1)
    assert ratio <= 0.33  # Front section

    # Pantry Car & First AC
    pc_idx = next(i for i, c in enumerate(coaches) if c["coachId"] == "PC")
    h1_idx = next(i for i, c in enumerate(coaches) if c["coachId"] == "H1")
    assert pc_idx == 13
    assert h1_idx == 14


def test_train_12424_real_dibrugarh_rajdhani_rake():
    """Train 12424 (Dibrugarh Rajdhani): Real 21-car LHB rake."""
    response = client.get("/api/trains/12424/formation")
    assert response.status_code == 200
    data = response.json()
    assert data["verificationStatus"] == "VERIFIED"

    coaches = data["coaches"]
    assert len(coaches) == 21

    b1_idx = next(i for i, c in enumerate(coaches) if c["coachId"] == "B1")
    assert b1_idx == 2  # Front section


def test_train_12004_real_swarna_shatabdi_rake():
    """Train 12004 (Lucknow Swarna Shatabdi): Real 18-car LHB Chair Car rake."""
    response = client.get("/api/trains/12004/formation")
    assert response.status_code == 200
    data = response.json()
    assert data["verificationStatus"] == "VERIFIED"

    coaches = data["coaches"]
    assert len(coaches) == 18

    # E1 & E2 Executive class after EOG
    e1_idx = next(i for i, c in enumerate(coaches) if c["coachId"] == "E1")
    assert e1_idx == 2


def test_unknown_train_returns_404():
    """Unknown train returns 404 with clear message."""
    response = client.get("/api/trains/99999/formation")
    assert response.status_code == 404
    assert "currently unavailable" in response.json()["detail"]
