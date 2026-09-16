"""
Integration tests for FastAPI Backend endpoints.
Validates HTTP contracts, deep health check, optimizer, and telemetry feeds.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_health():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "SIH26028" in data["system"]


def test_deep_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("HEALTHY", "DEGRADED")
    assert "subsystems" in data
    subsystems = data["subsystems"]
    assert "api" in subsystems
    assert "ml_inference" in subsystems
    assert "railway_feed" in subsystems
    assert "weather_cache" in subsystems
    assert "websocket" in subsystems
    assert subsystems["api"]["status"] == "HEALTHY"


def test_api_sections_listing():
    response = client.get("/api/sections")
    assert response.status_code == 200
    sections = response.json()
    assert isinstance(sections, list)
    assert len(sections) > 0
    sec_ids = [s["section_id"] for s in sections]
    assert "KNP-PRYJ-SEC-B" in sec_ids


def test_api_trains_for_section():
    response = client.get("/api/trains?section_id=KNP-PRYJ-SEC-B")
    assert response.status_code == 200
    trains = response.json()
    assert isinstance(trains, list)
    assert len(trains) > 0
    t_nums = [t["train_number"] for t in trains]
    assert "22436" in t_nums


def test_api_optimizer_solve_endpoint():
    payload = {
        "block_id": "MNT-TEST-01",
        "section_id": "KNP-PRYJ-SEC-B",
        "duration_minutes": 120,
        "earliest_start_min": 600,
        "latest_end_min": 900,
        "work_type": "Rail Replacement",
        "override_weather_risk": "LOW"
    }
    response = client.post("/api/optimizer/solve", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] in ("OPTIMAL_SCHEDULED", "NO_FEASIBLE_SLOT")
    if res["status"] == "OPTIMAL_SCHEDULED":
        assert res["duration_minutes"] == 120
        assert res["allocated_end_min"] - res["allocated_start_min"] == 120


def test_api_conflicts_check():
    payload = {
        "section_id": "KNP-PRYJ-SEC-B",
        "proposed_start_min": 630,
        "proposed_end_min": 660
    }
    response = client.post("/api/conflicts/check", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["section_id"] == "KNP-PRYJ-SEC-B"
    assert "has_conflict" in res


def test_api_dynamic_eta_prediction_endpoint():
    payload = {
        "train_id": "22436",
        "current_station": "Kanpur Central",
        "next_station": "Fatehpur",
        "destination": "Prayagraj Junction",
        "speed_kmph": 110.0,
        "distance_remaining_km": 194.0,
        "priority": 2,
    }
    response = client.post("/api/trains/eta", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["train_id"] == "22436"
    assert data["model_used"] == "XGBoost"
    assert data["predicted_remaining_travel_time"] > 0
    assert data["prediction_status"] in ("NOMINAL", "DELAYED")
    assert "predicted_arrival_time" in data


def test_api_active_train_dynamic_eta():
    response = client.get("/api/trains/22436/eta")
    assert response.status_code == 200
    data = response.json()
    assert data["train_id"] == "22436"
    assert data["model_used"] == "XGBoost"
    assert data["predicted_remaining_travel_time"] >= 0
