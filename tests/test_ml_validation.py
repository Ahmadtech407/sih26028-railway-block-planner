"""
Validation tests for Trained Machine Learning XGBoost Delay & Dynamic ETA Models.
Verifies model serialization, 5-fold cross-validation metrics, probability extraction,
feature engineering, dynamic ETA calculation, and fallback mechanisms.
"""

import pytest
from backend.services import ml_prediction_service as ml
from backend.ml.feature_engineering import create_eta_features


def test_model_metadata_and_5fold_cv():
    info = ml.get_model_info()
    assert info["status"] == "LOADED"
    assert "IR-XGB-DelayPredictor-v3.0" in info["model_version"]
    assert "XGBoost" in info["primary_eta_model"]
    assert info["congestion_accuracy"] >= 0.90
    assert info["congestion_classification_f1"] >= 0.90
    assert info["delay_regression_mae"] <= 1.0


def test_predict_congestion_with_probability():
    level, prob = ml.predict_congestion_with_probability(
        priority=2,
        speed_kmph=112.0,
        weather_risk="LOW",
        delay_minutes=0
    )
    assert level in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0


def test_delay_prediction_bounds_and_regulation():
    # Premium express train (priority 2) should be regulated/clamped reasonably
    delay = ml.predict_delay_minutes("22436", speed_kmph=112.0, current_delay=0, priority=2)
    assert isinstance(delay, int)
    assert 0 <= delay <= 10  # Premium priority regulated tightly

    # Normal passenger train with severe weather
    delay_bad_weather = ml.predict_delay_minutes(
        "15018",
        speed_kmph=40.0,
        current_delay=10,
        weather_risk="EXTREME",
        congestion_level="HIGH",
        priority=3
    )
    assert isinstance(delay_bad_weather, int)
    assert delay_bad_weather >= 10  # Delay increases under extreme conditions


def test_feature_engineering_pipeline():
    # Test with standard state
    df = create_eta_features({
        "current_speed": 110.0,
        "distance_remaining": 150.0,
        "priority": 2,
        "weather": "Rainy",
    })
    assert len(df) == 1
    assert df["speed_kmph"].iloc[0] == 110.0
    assert df["distance_remaining_km"].iloc[0] == 150.0
    assert df["Weather"].iloc[0] == "Rainy"

    # Test with completely missing/empty state (safe imputation)
    df_empty = create_eta_features({})
    assert len(df_empty) == 1
    assert not df_empty.isnull().any().any()


def test_dynamic_eta_prediction_structure():
    res = ml.predict_dynamic_eta({
        "train_id": "22436",
        "current_station": "Kanpur Central",
        "destination": "Prayagraj Junction",
        "speed_kmph": 100.0,
        "distance_remaining_km": 200.0,
        "priority": 2,
    })
    assert res["train_id"] == "22436"
    assert res["predicted_remaining_travel_time"] > 0
    assert res["model_used"] == "XGBoost"
    assert res["prediction_status"] in ("NOMINAL", "DELAYED")
    assert ":" in res["predicted_arrival_time"]


def test_dynamic_eta_edge_cases():
    # 1. Train at destination -> 0 remaining time
    res_arrived = ml.predict_dynamic_eta({
        "train_id": "12301",
        "distance_remaining_km": 0.0,
        "speed_kmph": 0.0,
    })
    assert res_arrived["predicted_remaining_travel_time"] == 0
    assert res_arrived["prediction_status"] == "ARRIVED"

    # 2. Unexpected stop -> STOPPED status and extra dwell delay
    res_stopped = ml.predict_dynamic_eta({
        "train_id": "12301",
        "distance_remaining_km": 100.0,
        "speed_kmph": 0.0,
        "current_delay": 5,
    })
    assert res_stopped["prediction_status"] == "STOPPED"
    assert res_stopped["predicted_remaining_travel_time"] > 0

    # 3. Dynamic adjustment: slower speed results in longer remaining travel time
    fast = ml.predict_dynamic_eta({"distance_remaining_km": 100.0, "speed_kmph": 120.0})
    slow = ml.predict_dynamic_eta({"distance_remaining_km": 100.0, "speed_kmph": 40.0})
    assert slow["predicted_remaining_travel_time"] > fast["predicted_remaining_travel_time"]


def test_dynamic_eta_physical_kinematics_and_gradient():
    # Heavy freight (5200t) on rising gradient (+1.0%) should experience deceleration resistance
    flat_freight = ml.predict_dynamic_eta({
        "train_id": "BCNA",
        "train_mass_tonnes": 5200.0,
        "track_gradient_pct": 0.0,
        "speed_kmph": 60.0,
        "distance_remaining_km": 50.0,
        "priority": 5,
    })
    uphill_freight = ml.predict_dynamic_eta({
        "train_id": "BCNA",
        "train_mass_tonnes": 5200.0,
        "track_gradient_pct": 1.0,
        "speed_kmph": 60.0,
        "distance_remaining_km": 50.0,
        "priority": 5,
    })
    assert uphill_freight["predicted_remaining_travel_time"] >= flat_freight["predicted_remaining_travel_time"]
    assert uphill_freight["train_mass_tonnes"] == 5200.0
    assert uphill_freight["track_gradient_pct"] == 1.0


def test_dynamic_eta_fog_speed_cap():
    # Clear weather allows high speed 130 km/h; fog caps effective speed to 75 km/h
    clear = ml.predict_dynamic_eta({
        "train_id": "22436",
        "speed_kmph": 130.0,
        "weather_risk": "LOW",
        "distance_remaining_km": 100.0,
    })
    fog = ml.predict_dynamic_eta({
        "train_id": "22436",
        "speed_kmph": 130.0,
        "weather_risk": "FOG_DENSE",
        "distance_remaining_km": 100.0,
    })
    assert fog["predicted_remaining_travel_time"] > clear["predicted_remaining_travel_time"]


def test_dynamic_eta_telemetry_latency_decay():
    # Telemetry older than 120 seconds enters DEGRADED_TELEMETRY status with decayed confidence
    fresh = ml.predict_dynamic_eta({
        "train_id": "12802",
        "speed_kmph": 90.0,
        "distance_remaining_km": 60.0,
        "data_age_seconds": 10.0,
    })
    stale = ml.predict_dynamic_eta({
        "train_id": "12802",
        "speed_kmph": 90.0,
        "distance_remaining_km": 60.0,
        "data_age_seconds": 180.0,
    })
    assert stale["confidence"] < fresh["confidence"]
    assert stale["prediction_status"] == "DEGRADED_TELEMETRY"

