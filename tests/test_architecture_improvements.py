"""
Comprehensive Verification Tests for Architecture & Technical Improvements
========================================================================
Covers all 6 priority improvement areas:
1. Frontend Real ML ETA & Destination Alarm resolution
2. Supabase failure handling & Pre-flight URL validation
3. Local SQLite embedded fallback persistence
4. Unified dynamic train ML predictions (Champion Ensemble)
5. HTTP connection pooling and keep-alive
6. Closed-loop ML retraining pipeline & Champion gatekeeper
"""

import os
import sqlite3
import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from backend.supa_client import is_supabase_configured, TableQuery, _get_http_session, SupabaseRestClient
from backend.services.supabase_train_store import (
    LOCAL_DB_PATH,
    store_telemetry,
    get_telemetry_history,
    store_ml_prediction,
    get_latest_ml_prediction,
    get_ml_training_data,
)
from backend.services.train_service import get_trains_for_section
from backend.ml.retrain_pipeline import (
    validate_dataset,
    evaluate_against_champion,
    fetch_retraining_data,
)
from passenger_app import destination_eta_minutes


def test_supabase_preflight_and_unconfigured_safety():
    """Verify that unconfigured Supabase executes cleanly without network or URL errors."""
    with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SECRET_KEY": ""}):
        assert not is_supabase_configured()

        client = SupabaseRestClient("", "")
        query = client.table("train_live_positions").select("*")
        response = query.execute()

        assert response.data is None
        assert response.error == "SUPABASE_UNCONFIGURED"


def test_http_session_pooling_and_retries():
    """Verify thread-local session uses HTTPAdapter with connection pooling and retries."""
    session = _get_http_session()
    assert session is not None
    adapter = session.adapters.get("https://")
    assert adapter is not None
    assert adapter._pool_connections == 10
    assert adapter._pool_maxsize == 20
    assert adapter.max_retries.total == 3


def test_local_sqlite_fallback_telemetry_and_predictions():
    """Verify embedded SQLite database persists and retrieves live positions and ML predictions."""
    test_train_no = "TEST_99999"

    # Store telemetry
    res = store_telemetry(
        train_number=test_train_no,
        section_id="TEST-SEC",
        position_km=420.5,
        speed_kmph=88.0,
        delay_minutes=7,
        congestion_level="MEDIUM",
        gps_lat=26.45,
        gps_lon=80.35,
        data_source="TEST_SUITE",
    )
    assert res is True

    # Retrieve history
    history = get_telemetry_history(test_train_no, limit=5)
    assert len(history) >= 1
    latest = history[0]
    assert latest["train_id"] == test_train_no
    assert float(latest["speed_kmph"]) == 88.0

    # Store ML prediction
    ml_res = store_ml_prediction(
        train_number=test_train_no,
        predicted_delay_minutes=8.5,
        predicted_congestion_level="MEDIUM",
        congestion_probability=0.72,
        confidence_score=0.96,
        model_name="Champion_Ensemble",
        model_version="3.1.0",
    )
    assert ml_res is True

    # Retrieve latest ML prediction
    latest_ml = get_latest_ml_prediction(test_train_no)
    assert latest_ml is not None
    assert latest_ml["train_id"] == test_train_no
    assert float(latest_ml["predicted_delay_minutes"]) == 8.5
    assert latest_ml["model_name"] == "Champion_Ensemble"

    # Verify retrieval for retraining data
    training_data = get_ml_training_data(limit=10)
    assert len(training_data) >= 1


def test_unified_train_ml_predictions_in_feed():
    """Verify that train feed returns unified dynamic ML predictions from Champion Ensemble."""
    trains = get_trains_for_section("KNP-PRYJ-SEC-B")
    assert len(trains) > 0

    for train in trains:
        assert train.predicted_remaining_travel_time is not None
        assert isinstance(train.predicted_remaining_travel_time, int)
        assert train.predicted_remaining_travel_time >= 0
        assert train.predicted_delay_minutes is not None
        assert train.model_used in ("Ensemble", "XGBoost", "Random Forest", "SVR", "Gradient Boosting", "Decision Tree")


def test_passenger_frontend_eta_resolution():
    """Verify passenger_app destination_eta_minutes prioritizes real ML travel time and falls back properly."""
    section = {"start_km": 400.0, "end_km": 442.5}

    # Case 1: Train has precomputed ML remaining travel time
    train_with_ml = {
        "train_number": "12301",
        "speed_kmph": 80.0,
        "position_km": 410.0,
        "direction": "UP",
        "predicted_remaining_travel_time": 27,
        "delay_minutes": 5,
    }
    eta = destination_eta_minutes(train_with_ml, section)
    assert eta == 27  # Must use real ML prediction, not (442.5-410)/80*60 = 24

    # Case 2: Train has no precomputed ML time, backend unreachable -> calibrated fallback with delay
    train_offline = {
        "train_number": "99999",
        "speed_kmph": 60.0,
        "position_km": 412.5,
        "direction": "UP",
        "delay_minutes": 10,
    }
    with patch("passenger_app.get_json", return_value=None):
        eta_calibrated = destination_eta_minutes(train_offline, section)
        # dist = 442.5 - 412.5 = 30 km. 30/60*60 = 30 min + 10 min delay = 40 min
        assert eta_calibrated == 40


def test_ml_retraining_dataset_validation():
    """Verify retraining dataset validation handles good and corrupt data correctly."""
    # Valid dataframe
    valid_df = pd.DataFrame({
        "target_remaining_travel_time_minutes": [35.0] * 60,
        "distance_remaining_km": [25.0] * 60,
        "speed_kmph": [80.0] * 60,
        "current_delay": [5.0] * 60,
        "StationOrder": [3] * 60,
        "halt_time_minutes": [5.0] * 60,
        "priority": [3] * 60,
    })
    is_valid, msg = validate_dataset(valid_df, min_samples=50)
    assert is_valid is True

    # Too few samples
    short_df = valid_df.head(20)
    is_valid, msg = validate_dataset(short_df, min_samples=50)
    assert is_valid is False
    assert "samples" in msg

    # Null target
    null_target_df = valid_df.copy()
    null_target_df.loc[0, "target_remaining_travel_time_minutes"] = None
    is_valid, msg = validate_dataset(null_target_df, min_samples=50)
    assert is_valid is False
    assert "null" in msg.lower() or "nan" in msg.lower()


def test_champion_gatekeeper_logic():
    """Verify gatekeeper approves superior candidate and rejects inferior candidate."""
    baseline = {
        "selected_production_model": "Ensemble",
        "models": {
            "Ensemble": {"MAE": 2.50},
            "Gradient Boosting": {"MAE": 2.65},
        }
    }

    # Better candidate (MAE 2.30 < 2.50) -> Approved
    better_candidate = {
        "selected_production_model": "Ensemble",
        "models": {
            "Ensemble": {"MAE": 2.30},
        }
    }
    approved, reason, cand_mae, curr_mae = evaluate_against_champion(better_candidate, baseline)
    assert approved is True
    assert cand_mae == 2.30
    assert curr_mae == 2.50
    assert "Promotion approved" in reason

    # Worse candidate (MAE 2.80 > 2.50) -> Rejected
    worse_candidate = {
        "selected_production_model": "Ensemble",
        "models": {
            "Ensemble": {"MAE": 2.80},
        }
    }
    approved, reason, cand_mae, curr_mae = evaluate_against_champion(worse_candidate, baseline)
    assert approved is False
    assert cand_mae == 2.80
    assert curr_mae == 2.50
    assert "REJECTED" in reason
