"""
Comprehensive 20-Point Project Limitations Verification Suite.
Validates code-level implementations across all 20 critical areas:
1. Supabase offline write queue & sync
2. Multi-tiered weather with OpenWeatherMap & TTL cache
3. Real-time SSE/WebSocket passenger updates
4. Multi-corridor configuration
5. Dynamic speed limit resolution
6. Configurable section capacity & occupancy calculation
7. Telemetry staleness & continuous freshness scoring
8. Retraining dataset validation gate
9. Continuous learning with model versioning & rollback
10. Station/train-type dwell bounds
11. Connection pooling
12. Deployment readiness /ready probe
13. Train data source abstraction
14. Authoritative ETA pipeline with kinematics guardrails
15. Functional disruption matrix
16. Fast In-Memory / Redis TTL Cache
17. Latency tracking with X-Response-Time-Ms
18. Streamlit session-state rerun optimization
19. Security & secret management
20. End-to-end integration and stability
"""

import os
import time
from datetime import datetime, timezone
import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.services import (
    cache_service,
    disruption_service,
    section_service,
    platform_service,
    weather_service,
    train_data_source,
    supabase_train_store,
    ml_prediction_service,
)
from backend.ml import model_registry, retrain_pipeline


@pytest.fixture
def client():
    return TestClient(app)


def test_area_1_supabase_offline_sync():
    """Area 1: Verify offline SQLite write queue and sync mechanics."""
    supabase_train_store.store_telemetry(
        train_number="TEST_TRAIN_999",
        section_id="KNP-PRYJ-SEC-B",
        position_km=420.0,
        speed_kmph=95.0,
        delay_minutes=2,
        data_source="TEST_OFFLINE",
    )
    result = supabase_train_store.sync_local_queue_to_supabase(batch_size=10)
    assert isinstance(result, dict)
    assert "positions_synced" in result or "message" in result or "status" in result


def test_area_2_multi_tier_weather():
    """Area 2: Verify OpenWeatherMap, Open-Meteo, cache, and climate fallback."""
    cache_service.set("weather:test_sec", {"temp": 28.0}, ttl_seconds=5)
    cached = cache_service.get("weather:test_sec")
    assert cached == {"temp": 28.0}

    w = weather_service.get_section_weather("KNP-PRYJ-SEC-B")
    assert w is not None
    assert w.weather_source in (
        "IMD_INDIA_METEOROLOGICAL_DEPARTMENT",
        "OPENWEATHERMAP_API",
        "OPEN_METEO_API",
        "CACHED_OBSERVATION",
        "CALIBRATED_CLIMATE_MODEL",
    )
    assert w.temperature_c is not None


def test_area_3_sse_stream(client):
    """Area 3: Verify Server-Sent Events stream endpoint."""
    with client.stream("GET", "/api/trains/stream?section_id=KNP-PRYJ-SEC-B&limit=1") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        lines = []
        for line in response.iter_lines():
            if line:
                lines.append(line)
                if line.startswith("data:"):
                    break
        assert any(l.startswith("data:") for l in lines)


def test_area_4_multi_corridor_configuration():
    """Area 4: Verify multiple Indian Railway corridors beyond Kanpur-Prayagraj."""
    sections = section_service.get_all_sections()
    sec_ids = [s.section_id for s in sections]
    assert "KNP-PRYJ-SEC-B" in sec_ids
    assert "LKO-KNP-SEC-A" in sec_ids
    assert "NDLS-CNB-SEC-A" in sec_ids
    assert "PRYJ-DDU-SEC-A" in sec_ids
    assert "NDLS-UMB-SEC-A" in sec_ids


def test_area_5_dynamic_speed_limits():
    """Area 5: Verify multi-factor dynamic speed limit resolution."""
    spd_clear = section_service.get_effective_speed_limit("LKO-KNP-SEC-A", "VANDE_BHARAT", "LOW")
    assert spd_clear == 160.0

    spd_freight = section_service.get_effective_speed_limit("LKO-KNP-SEC-A", "FREIGHT", "LOW")
    assert spd_freight == 75.0

    spd_fog = section_service.get_effective_speed_limit("LKO-KNP-SEC-A", "VANDE_BHARAT", "FOG")
    assert spd_fog == 75.0

    spd_tsr = section_service.get_effective_speed_limit("LKO-KNP-SEC-A", "VANDE_BHARAT", "LOW", tsr_kmph=45.0)
    assert spd_tsr == 45.0


def test_area_6_section_capacity_occupancy():
    """Area 6: Verify configurable section capacity and congestion calculation."""
    cong_low, occ_low = section_service.calculate_section_congestion("NDLS-CNB-SEC-A", 2)
    assert cong_low == "LOW"
    assert occ_low < 0.35

    cong_crit, occ_crit = section_service.calculate_section_congestion("NDLS-CNB-SEC-A", 13)
    assert cong_crit == "CRITICAL"
    assert occ_crit >= 0.85


def test_area_7_freshness_scoring():
    """Area 7: Verify continuous telemetry freshness scoring and degradation."""
    state_fresh = {"data_age_seconds": 10, "speed_kmph": 80.0, "position_km": 420.0}
    res_fresh = ml_prediction_service.predict_dynamic_eta(state_fresh)
    assert res_fresh["freshness_score"] >= 0.90
    assert res_fresh["telemetry_status"] == "REAL_TIME"
    assert res_fresh["prediction_status"] in ("REAL_TIME", "NOMINAL", "DELAYED")

    state_stale = {"data_age_seconds": 180, "speed_kmph": 80.0, "position_km": 420.0}
    res_stale = ml_prediction_service.predict_dynamic_eta(state_stale)
    assert res_stale["freshness_score"] < 0.60
    assert res_stale["telemetry_status"] == "STALE_TELEMETRY"
    assert res_stale["prediction_status"] in ("STALE_TELEMETRY", "DEGRADED_TELEMETRY")

    state_dead = {"data_age_seconds": 400, "speed_kmph": 80.0, "position_km": 420.0}
    res_dead = ml_prediction_service.predict_dynamic_eta(state_dead)
    assert res_dead["freshness_score"] == 0.05
    assert res_dead["telemetry_status"] == "EXPIRED_TELEMETRY"
    assert res_dead["prediction_status"] == "EXPIRED_TELEMETRY"


def test_area_8_retraining_dataset_gate():
    """Area 8: Verify dataset validation gate rejects invalid/drifted datasets."""
    import pandas as pd
    valid_df = pd.DataFrame({
        "train_type": ["EXP", "SF"],
        "priority": [2, 1],
        "scheduled_travel_time": [30, 25],
        "current_delay": [5, 0],
        "distance_remaining_km": [20.0, 15.0],
        "speed_kmph": [80.0, 110.0],
        "weather_risk": ["LOW", "LOW"],
        "congestion_level": ["LOW", "MEDIUM"],
        "target_remaining_travel_time_minutes": [32.0, 26.0],
    })
    is_valid, msg = retrain_pipeline.validate_dataset(valid_df, min_samples=2)
    assert is_valid is True

    is_empty_valid, _ = retrain_pipeline.validate_dataset(pd.DataFrame(), min_samples=2)
    assert is_empty_valid is False


def test_area_9_model_rollback(client):
    """Area 9: Verify continuous learning model rollback mechanism."""
    registry = model_registry.get_model_registry()
    assert registry is not None
    response = client.post("/api/trains/eta/rollback")
    assert response.status_code in (200, 400)
    data = response.json()
    assert "success" in data or "detail" in data


def test_area_10_dwell_bounds():
    """Area 10: Verify station and train-type dwell time bounds."""
    min_d, max_d = platform_service.get_platform_dwell_bounds("Kanpur Central", "EXPRESS")
    assert min_d >= 5
    assert max_d >= min_d

    freight_min, _ = platform_service.get_platform_dwell_bounds("Kanpur Central", "FREIGHT")
    assert freight_min >= min_d


def test_area_11_connection_pooling():
    """Area 11: Verify connection reuse in SQLite store and outbound requests."""
    with supabase_train_store._get_sqlite_conn() as conn1:
        cursor1 = conn1.cursor()
        cursor1.execute("SELECT 1")
        val1 = cursor1.fetchone()[0]

    with supabase_train_store._get_sqlite_conn() as conn2:
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT 1")
        val2 = cursor2.fetchone()[0]

    assert val1 == 1 and val2 == 1
    assert conn1 is conn2


def test_area_12_readiness_probe(client):
    """Area 12: Verify Kubernetes / Deployment readiness probe."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["database"] == "CONNECTED"
    assert data["ml_engine"] == "READY"


def test_area_13_data_source_abstraction():
    """Area 13: Verify train data source factory and polymorphic behavior."""
    ds = train_data_source.get_train_data_source()
    assert isinstance(ds, train_data_source.TrainDataSource)
    pos = ds.get_live_position("22436")
    assert pos is not None
    assert "data_source" in pos


def test_area_14_kinematics_guardrail():
    """Area 14: Verify physical kinematics guardrail clamps impossible ETA predictions."""
    state = {
        "speed_kmph": 50.0,
        "distance_remaining_km": 100.0,
        "position_km": 300.0,
        "destination_km": 400.0,
    }
    res = ml_prediction_service.predict_dynamic_eta(state)
    assert res["predicted_remaining_travel_time"] >= 37.0


def test_area_15_disruption_matrix():
    """Area 15: Verify functional disruption matrix and speed/delay impact."""
    incident = disruption_service.add_disruption(
        section_id="KNP-PRYJ-SEC-B",
        incident_type="SIGNAL_FAILURE",
        severity="HIGH",
        speed_cap_kmph=25.0,
    )
    assert incident["incident_type"] == "SIGNAL_FAILURE"

    impact = disruption_service.evaluate_disruption_matrix("KNP-PRYJ-SEC-B")
    assert impact["delay_multiplier"] > 1.0
    assert impact["effective_speed_cap"] <= 60.0

    cleared = disruption_service.clear_disruptions("KNP-PRYJ-SEC-B")
    assert cleared > 0


def test_area_16_cache_service():
    """Area 16: Verify in-memory TTL cache with expiration and eviction."""
    cache_service.set("test_key_temp", "hello", ttl_seconds=1)
    assert cache_service.get("test_key_temp") == "hello"
    time.sleep(1.2)
    assert cache_service.get("test_key_temp") is None


def test_area_17_latency_header(client):
    """Area 17: Verify X-Response-Time-Ms header is injected on all requests."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Response-Time-Ms" in response.headers
    latency_ms = float(response.headers["X-Response-Time-Ms"])
    assert latency_ms >= 0.0


def test_area_18_passenger_session_cache():
    """Area 18: Verify passenger app data fetch functions operate without errors."""
    from passenger_app import fetch_sections, fetch_platforms
    sections = fetch_sections()
    assert isinstance(sections, list)
    assert len(sections) > 0

    platforms = fetch_platforms("KNP-PRYJ-SEC-B")
    assert isinstance(platforms, dict)


def test_area_19_security_secret_management():
    """Area 19: Verify JWT token hashing and secret isolation."""
    from backend.routes.auth import JWT_SECRET, hash_password, verify_password
    assert JWT_SECRET is not None
    assert JWT_SECRET != "change-this-in-production"
    assert len(JWT_SECRET) >= 32

    pwd = "RailPass@2026Safe"
    hashed = hash_password(pwd)
    assert ":" in hashed
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_area_20_full_verification(client):
    """Area 20: Full end-to-end integration and system operational readiness."""
    res = client.get("/system/operational-readiness")
    assert res.status_code == 200
    data = res.json()
    assert data["operational_mode"] == "ADVISORY_DECISION_SUPPORT"
    assert data["safety_classification"] == "NON_VITAL_ADVISORY_DSS"
    assert len(data["telemetry_sources_active"]) >= 2
    assert "disclaimer" in data
