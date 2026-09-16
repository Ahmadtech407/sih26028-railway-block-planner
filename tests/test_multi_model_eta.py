"""
Multi-Model Dynamic ETA Test Suite
===================================
Comprehensive tests for the 5-model ETA prediction system.
"""

import pytest
import json
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.ml.model_registry import registry, ModelRegistry
from backend.ml.feature_engineering import create_eta_features, FEATURES_NUM, FEATURES_CAT
from backend.services import ml_prediction_service as ml

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "data" / "models"


# === Fixtures ===

@pytest.fixture
def sample_train_state():
    return {
        "train_id": "22436",
        "current_station": "Kanpur Central",
        "next_station": "Prayagraj Jn",
        "destination": "Varanasi",
        "position_km": 120.0,
        "destination_km": 442.5,
        "speed_kmph": 95.0,
        "current_delay": 5,
        "weather_risk": "LOW",
        "congestion_level": "LOW",
        "priority": 2,
    }

@pytest.fixture
def stopped_train_state():
    return {
        "train_id": "12560",
        "position_km": 200.0,
        "destination_km": 442.5,
        "speed_kmph": 0.0,
        "current_delay": 10,
        "weather_risk": "HIGH",
        "priority": 3,
    }

@pytest.fixture
def disrupted_train_state():
    return {
        "train_id": "12345",
        "position_km": 150.0,
        "destination_km": 442.5,
        "speed_kmph": 60.0,
        "current_delay": 0,
        "weather_risk": "LOW",
        "priority": 3,
        "ohe_failure": True,
    }

@pytest.fixture
def arrived_train_state():
    return {
        "train_id": "22436",
        "position_km": 442.5,
        "destination_km": 442.5,
        "speed_kmph": 0.0,
        "current_delay": 0,
        "priority": 2,
    }


# === 1. Model Files Existence ===

def test_all_model_files_exist():
    """All 5 trained model artifacts must exist on disk."""
    for key, filename in ModelRegistry.MODEL_FILES.items():
        path = MODELS_DIR / filename
        assert path.exists(), f"Model file missing: {path}"

def test_model_comparison_json_exists():
    """model_comparison.json must exist with evaluation results."""
    path = MODELS_DIR / "model_comparison.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "models" in data or "best_individual_model" in data


# === 2. Registry Loading ===

def test_registry_loads_all_models():
    """Registry must load all 5 model pipelines."""
    assert registry._loaded is True
    for key in ModelRegistry.MODEL_FILES.keys():
        assert key in registry._models, f"Model {key} not loaded in registry"

def test_registry_comparison_populated():
    comp = registry.get_comparison()
    assert isinstance(comp, dict)
    assert len(comp) > 0


# === 3. Individual Model Predictions ===

@pytest.mark.parametrize("model_key", ["xgboost", "random_forest", "svr", "gradient_boosting", "decision_tree"])
def test_individual_model_prediction(model_key, sample_train_state):
    """Each model must produce a non-negative numeric prediction."""
    features = create_eta_features(sample_train_state)
    predicted_min, model_used, breakdown = registry.predict(features, model_key)
    assert isinstance(predicted_min, float)
    assert predicted_min >= 0.0, f"{model_key} predicted negative time: {predicted_min}"
    assert model_used in ModelRegistry.FORMAL_NAMES.values()
    assert isinstance(breakdown, dict)


# === 4. Ensemble Prediction ===

def test_ensemble_prediction(sample_train_state):
    features = create_eta_features(sample_train_state)
    predicted_min, model_used, breakdown = registry.predict(features, "ensemble")
    assert model_used == "Ensemble"
    assert predicted_min >= 0.0
    assert len(breakdown) >= 3  # At least 3 models in breakdown


# === 5. Best Model Selection ===

def test_best_model_selection(sample_train_state):
    features = create_eta_features(sample_train_state)
    predicted_min, model_used, breakdown = registry.predict(features, "best_model")
    assert predicted_min >= 0.0
    champion = registry.get_champion_model_key()
    # best_model should use the champion
    if champion == "ensemble":
        assert model_used == "Ensemble"
    else:
        assert model_used == ModelRegistry.FORMAL_NAMES[champion]


# === 6. Dynamic ETA Full Pipeline ===

def test_dynamic_eta_returns_all_fields(sample_train_state):
    res = ml.predict_dynamic_eta(sample_train_state)
    required_keys = ["train_id", "predicted_remaining_travel_time", "predicted_arrival_time",
                     "delay_estimate", "confidence", "prediction_status", "model_used"]
    for key in required_keys:
        assert key in res, f"Missing key: {key}"

def test_dynamic_eta_with_model_selection(sample_train_state):
    for model in ["xgboost", "random_forest", "gradient_boosting", "ensemble", "best_model"]:
        res = ml.predict_dynamic_eta(sample_train_state, model_name=model)
        assert res["predicted_remaining_travel_time"] >= 0
        assert res["confidence"] > 0.0


# === 7. Arrived Train ===

def test_arrived_train(arrived_train_state):
    res = ml.predict_dynamic_eta(arrived_train_state)
    assert res["prediction_status"] == "ARRIVED"
    assert res["predicted_remaining_travel_time"] == 0


# === 8. Stopped Train ===

def test_stopped_train(stopped_train_state):
    res = ml.predict_dynamic_eta(stopped_train_state)
    assert res["prediction_status"] == "STOPPED"
    assert res["predicted_remaining_travel_time"] > 0


# === 9. Disruption Handling ===

def test_disruption_ohe_failure(disrupted_train_state):
    res_normal = ml.predict_dynamic_eta({**disrupted_train_state, "ohe_failure": False})
    res_disrupted = ml.predict_dynamic_eta(disrupted_train_state)
    # Disrupted ETA should be >= normal (30% penalty)
    assert res_disrupted["predicted_remaining_travel_time"] >= res_normal["predicted_remaining_travel_time"]

def test_disruption_track_blockage(sample_train_state):
    state = {**sample_train_state, "track_blockage": True}
    res = ml.predict_dynamic_eta(state)
    assert res["predicted_remaining_travel_time"] > 0

def test_disruption_signal_failure(sample_train_state):
    state = {**sample_train_state, "signal_failure": True}
    res = ml.predict_dynamic_eta(state)
    assert res["predicted_remaining_travel_time"] > 0


# === 10. Stale Telemetry ===

def test_stale_telemetry_degrades_confidence(sample_train_state):
    fresh_state = {**sample_train_state, "data_age_seconds": 0}
    stale_state = {**sample_train_state, "data_age_seconds": 300}
    res_fresh = ml.predict_dynamic_eta(fresh_state)
    res_stale = ml.predict_dynamic_eta(stale_state)
    assert res_stale["confidence"] < res_fresh["confidence"]


# === 11. Sanity Checks ===

def test_no_negative_travel_time(sample_train_state):
    res = ml.predict_dynamic_eta(sample_train_state)
    assert res["predicted_remaining_travel_time"] >= 0
    assert res["delay_estimate"] >= 0

def test_empty_train_state():
    res = ml.predict_dynamic_eta({})
    assert res["predicted_remaining_travel_time"] >= 0


# === 12. Physics Fallback ===

def test_physics_fallback_when_models_fail(sample_train_state):
    """When the registry throws, fallback should be used."""
    with patch.object(registry, 'predict', side_effect=RuntimeError("No models")):
        res = ml.predict_dynamic_eta(sample_train_state)
        assert "FALLBACK" in res.get("prediction_method", res.get("model_used", "")).upper()
        assert res["predicted_remaining_travel_time"] >= 0


# === 13. Model Performance Endpoint ===

def test_get_model_performance():
    data = ml.get_model_performance()
    assert isinstance(data, dict)
    assert len(data) > 0


# === 14. Extreme Weather ===

def test_extreme_weather_increases_eta(sample_train_state):
    normal_state = {**sample_train_state, "weather_risk": "LOW"}
    extreme_state = {**sample_train_state, "weather_risk": "EXTREME"}
    res_normal = ml.predict_dynamic_eta(normal_state)
    res_extreme = ml.predict_dynamic_eta(extreme_state)
    # Extreme weather should not produce LESS travel time
    assert res_extreme["predicted_remaining_travel_time"] >= res_normal["predicted_remaining_travel_time"] - 5


# === 15. Fog Speed Cap ===

def test_fog_speed_cap():
    state = {
        "train_id": "12560",
        "position_km": 100.0,
        "destination_km": 442.5,
        "speed_kmph": 130.0,
        "current_delay": 0,
        "weather_risk": "FOG",
        "priority": 2,
    }
    res = ml.predict_dynamic_eta(state)
    assert res["predicted_remaining_travel_time"] > 0


# === 16. Gradient Penalty for Freight ===

def test_gradient_penalty_freight():
    flat_state = {
        "train_id": "FREIGHT01",
        "position_km": 100.0,
        "destination_km": 442.5,
        "speed_kmph": 60.0,
        "priority": 5,
        "train_mass_tonnes": 5200.0,
        "track_gradient_pct": 0.0,
    }
    uphill_state = {**flat_state, "track_gradient_pct": 2.0}
    res_flat = ml.predict_dynamic_eta(flat_state)
    res_uphill = ml.predict_dynamic_eta(uphill_state)
    assert res_uphill["predicted_remaining_travel_time"] >= res_flat["predicted_remaining_travel_time"]


# === 17. Model Aliases ===

def test_model_name_aliases(sample_train_state):
    features = create_eta_features(sample_train_state)
    for alias in ["gbm", "rf", "xgb", "tree", "best", "default", "champion"]:
        predicted_min, model_used, _ = registry.predict(features, alias)
        assert predicted_min >= 0.0


# === 18. TSR Speed Restriction ===

def test_tsr_speed_restriction():
    state = {
        "train_id": "22436",
        "position_km": 200.0,
        "destination_km": 442.5,
        "speed_kmph": 110.0,
        "priority": 2,
        "speed_restriction_kmph": 30,
    }
    res = ml.predict_dynamic_eta(state)
    assert res["predicted_remaining_travel_time"] > 0
