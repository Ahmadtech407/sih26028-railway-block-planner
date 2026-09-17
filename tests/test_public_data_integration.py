"""
Tests for Public Railway Data Integration & Training Pipeline
=============================================================
Validates:
1. Dataset Catalog documentation (sources, licenses, date ranges, target variables)
2. Leakage Auditor (identifies post-trip variables, ensures 0 leakage in training matrix)
3. Quality Pipeline (validates physics bounds: speed, delay, impossible travel times)
4. Strict Chronological Temporal Splits (train -> val -> test, zero temporal overlap)
5. Multi-Model Architecture & Ensemble (XGBoost, RF, SVR, GBM, DT + SLSQP weights)
6. Dynamic Inference & Physical Kinematic Guardrails (t >= d / effective_max_speed)
7. Fast-API Endpoints (/trains/eta/model-performance, /trains/eta/predict)
"""

import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.ml.data.leakage_audit import LeakageAuditor, SAFE_FEATURES, LEAKED_FEATURES
from backend.ml.data.quality_pipeline import RailwayDataQualityPipeline
from backend.ml.feature_engineering import prepare_training_features, FEATURES_NUM, FEATURES_CAT
from backend.ml.model_registry import registry, ModelRegistry
from backend.services import ml_prediction_service as ml

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "backend" / "ml" / "data"
MODELS_DIR = BASE_DIR / "data" / "models"


@pytest.fixture
def client():
    return TestClient(app)


# ===========================================================================
# 1. DATASET CATALOG VALIDATION
# ===========================================================================

def test_dataset_catalog_structure():
    """Verify that dataset_catalog.json exists and adheres to the required schema."""
    catalog_path = DATA_DIR / "metadata" / "dataset_catalog.json"
    assert catalog_path.exists(), f"Catalog file missing at {catalog_path}"

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    assert "catalog_version" in catalog
    assert "datasets" in catalog
    assert len(catalog["datasets"]) >= 3, "Must catalog at least 3 distinct open railway datasets"

    required_fields = [
        "dataset_id", "name", "source", "url", "date_range",
        "columns", "target_variable", "limitations", "license"
    ]
    for ds in catalog["datasets"]:
        for field in required_fields:
            assert field in ds, f"Field '{field}' missing from dataset {ds.get('dataset_id')}"
            assert ds[field], f"Field '{field}' is empty in dataset {ds.get('dataset_id')}"


# ===========================================================================
# 2. FEATURE LEAKAGE AUDIT TESTS
# ===========================================================================

def test_leakage_auditor_detects_leaked_features():
    """Verify that LeakageAuditor flags known post-trip features as leaked."""
    auditor = LeakageAuditor()

    # Create dummy dataframe containing both safe and leaked features
    df = pd.DataFrame({
        "train_number": ["12423"],
        "speed": [110.0],
        "weather": ["CLEAR"],
        "distance_km": [48.0],
        "actual_arrival": ["2024-05-01 10:30:00"],
        "actual_travel_time": [28.0],
        "final_delay": [5.0],
        "post_trip_cause": ["SIGNAL"],
        "delay_minutes": [4.0],
    })

    report = auditor.audit_dataframe(df, target_col="delay_minutes")

    assert not report["is_leak_free"], "Dataframe with actual_arrival must NOT be flagged as leak-free"
    assert "actual_arrival" in report["leaked_features"]
    assert "actual_travel_time" in report["leaked_features"]
    assert "final_delay" in report["leaked_features"]
    assert "post_trip_cause" in report["leaked_features"]
    assert "train_number" in report["safe_features"]


def test_prepare_training_features_has_zero_leakage():
    """Verify that prepare_training_features outputs only SAFE features."""
    split_path = DATA_DIR / "processed" / "train_split.csv"
    assert split_path.exists(), "train_split.csv must exist"

    df_train = pd.read_csv(split_path, nrows=50)
    X, y_eta, y_delay = prepare_training_features(df_train)

    # Features must match exactly FEATURES_NUM + FEATURES_CAT
    expected_features = set(FEATURES_NUM + FEATURES_CAT)
    assert set(X.columns) == expected_features, "Feature matrix contains unauthorized or altered features"

    # None of the leaked features should appear in X
    for leaked in LEAKED_FEATURES:
        assert leaked not in X.columns, f"Leaked feature '{leaked}' found in training matrix!"

    # Targets must be valid numeric series
    assert not y_eta.isnull().any(), "ETA target contains nulls"
    assert not y_delay.isnull().any(), "Delay target contains nulls"
    assert (y_eta > 0).all(), "ETA targets must be strictly positive"


# ===========================================================================
# 3. DATA QUALITY PIPELINE & PHYSICAL BOUNDS
# ===========================================================================

def test_data_quality_report_exists():
    """Verify data_quality_report.json exists with recorded data sanitization metrics."""
    report_path = DATA_DIR / "metadata" / "data_quality_report.json"
    assert report_path.exists(), "data_quality_report.json must exist"

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert "records_loaded" in report
    assert "records_valid" in report
    assert "records_removed" in report
    assert report["records_valid"] > 1000, "Cleaned dataset should contain over 1000 operational records"


def test_quality_pipeline_physical_constraint_filtering():
    """Test that impossible physics records are flagged and removed by quality pipeline."""
    pipeline = RailwayDataQualityPipeline()

    bad_df = pd.DataFrame([
        # Row 1: Valid
        {"train_number": "12423", "speed": 100.0, "distance_km": 100.0, "scheduled_travel_time": 60.0, "actual_travel_time": 65.0, "delay_minutes": 5.0, "timestamp": "2024-01-01T00:00:00Z"},
        # Row 2: Impossible speed (> 160 km/h)
        {"train_number": "12424", "speed": 220.0, "distance_km": 100.0, "scheduled_travel_time": 60.0, "actual_travel_time": 65.0, "delay_minutes": 5.0, "timestamp": "2024-01-01T00:00:00Z"},
        # Row 3: Negative distance
        {"train_number": "12345", "speed": 80.0, "distance_km": -20.0, "scheduled_travel_time": 60.0, "actual_travel_time": 65.0, "delay_minutes": 5.0, "timestamp": "2024-01-01T00:00:00Z"},
        # Row 4: Travel time breaks kinematic speed of light on rail (100km in 10 minutes = 600 km/h)
        {"train_number": "12346", "speed": 100.0, "distance_km": 100.0, "scheduled_travel_time": 10.0, "actual_travel_time": 10.0, "delay_minutes": 0.0, "timestamp": "2024-01-01T00:00:00Z"},
    ])

    cleaned_df, report = pipeline.clean_and_audit(bad_df)
    assert len(cleaned_df) == 1, "Only row 1 should pass physical sanity constraints"
    assert cleaned_df.iloc[0]["train_number"] == "12423"


# ===========================================================================
# 4. CHRONOLOGICAL TEMPORAL SPLIT INTEGRITY
# ===========================================================================

def test_chronological_splits_integrity():
    """Verify that splits are strictly chronological with zero temporal overlap."""
    meta_path = DATA_DIR / "metadata" / "split_metadata.json"
    assert meta_path.exists(), "split_metadata.json must exist"

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["split_method"] == "STRICT_CHRONOLOGICAL_TEMPORAL"
    train_end = meta["train_date_range"][1]
    val_start = meta["val_date_range"][0]
    val_end = meta["val_date_range"][1]
    test_start = meta["test_date_range"][0]

    assert train_end <= val_start, "Train split leaks into Validation split chronologically"
    assert val_end <= test_start, "Validation split leaks into Test split chronologically"

    # Verify actual CSV dataframes
    train_df = pd.read_csv(DATA_DIR / "processed" / "train_split.csv")
    val_df = pd.read_csv(DATA_DIR / "processed" / "val_split.csv")
    test_df = pd.read_csv(DATA_DIR / "processed" / "test_split.csv")

    assert len(train_df) == meta["train_rows"]
    assert len(val_df) == meta["val_rows"]
    assert len(test_df) == meta["test_rows"]

    # Maximum timestamp in train must be <= minimum timestamp in test
    train_max_ts = pd.to_datetime(train_df["parsed_timestamp"], utc=True).max()
    test_min_ts = pd.to_datetime(test_df["parsed_timestamp"], utc=True).min()
    assert train_max_ts <= test_min_ts, "Test split contains timestamps earlier than training split!"


# ===========================================================================
# 5. MULTI-MODEL REGISTRY & ENSEMBLE EVALUATION
# ===========================================================================

def test_all_five_models_exist_and_loadable():
    """Verify all 5 distinct regression models exist in data/models/."""
    expected_models = [
        "xgboost_eta.joblib",
        "random_forest_eta.joblib",
        "svr_eta.joblib",
        "gradient_boosting_eta.joblib",
        "decision_tree_eta.joblib",
    ]
    for m in expected_models:
        path = MODELS_DIR / m
        assert path.exists(), f"Model artifact {m} missing from {MODELS_DIR}"

    assert registry._loaded is True
    assert len(registry._models) == 5


def test_model_comparison_and_metrics_validity():
    """Verify model comparison JSON contains all 5 models and ensemble metrics."""
    comp_path = MODELS_DIR / "model_comparison.json"
    assert comp_path.exists()

    with open(comp_path, "r", encoding="utf-8") as f:
        comp = json.load(f)

    models = comp["models"]
    for m in ["XGBoost", "Random Forest", "SVR", "Gradient Boosting", "Decision Tree", "Ensemble"]:
        assert m in models, f"Model '{m}' missing from comparison report"
        metrics = models[m]
        assert "MAE" in metrics and metrics["MAE"] > 0
        assert "RMSE" in metrics and metrics["RMSE"] > 0
        assert "R2" in metrics

    # Verify ensemble weights
    weights = comp.get("ensemble_weights", {})
    assert len(weights) == 5
    total_w = sum(weights.values())
    assert abs(total_w - 1.0) < 1e-3, f"Ensemble weights must sum to 1.0, got {total_w}"

    # Champion model must be defined
    champion = comp.get("selected_production_model")
    assert champion in ["Ensemble", "Random Forest", "XGBoost", "Gradient Boosting"]


# ===========================================================================
# 6. DYNAMIC PREDICTION & PHYSICAL KINEMATIC GUARDRAILS
# ===========================================================================

def test_predict_dynamic_eta_structure():
    """Verify predict_dynamic_eta returns standard schema with model breakdown."""
    state = {
        "train_id": "12423",
        "current_station": "Kanpur Central",
        "destination": "New Delhi",
        "speed_kmph": 90.0,
        "position_km": 100.0,
        "destination_km": 540.0,
        "distance_remaining_km": 440.0,
        "current_delay": 15,
        "weather_risk": "LOW",
        "congestion_level": "LOW",
        "priority": 2,
    }

    result = ml.predict_dynamic_eta(state, model_name="best_model")

    assert "predicted_remaining_travel_time" in result
    assert "predicted_arrival_time" in result
    assert "delay_estimate" in result
    assert "confidence" in result
    assert result["confidence"] >= 0.5
    assert result["prediction_status"] in ["NOMINAL", "DELAYED", "ARRIVED"]


def test_physical_kinematic_guardrail_enforcement():
    """
    Test physical constraint: train cannot arrive faster than maximum permissible speed.
    Remaining distance = 160 km, max speed limit = 160 km/h -> Minimum travel time = 60 minutes.
    ML cannot predict 10 minutes.
    """
    state = {
        "train_id": "12002",
        "current_station": "Mathura Jn",
        "destination": "New Delhi",
        "speed_kmph": 160.0,
        "distance_remaining_km": 160.0,
        "current_delay": 0,
        "weather_risk": "CLEAR",
        "congestion_level": "LOW",
        "priority": 1,
    }

    result = ml.predict_dynamic_eta(state, model_name="best_model")

    # At 160 km/h over 160 km, travel time cannot be < 60 minutes
    assert result["predicted_remaining_travel_time"] >= 60, (
        f"Kinematic guardrail violated: predicted {result['predicted_remaining_travel_time']} min for 160 km"
    )


def test_stopped_train_dwell_penalty():
    """Verify stopped train (speed=0) receives kinematic dwell penalty."""
    state_moving = {
        "train_id": "12423",
        "speed_kmph": 80.0,
        "distance_remaining_km": 80.0,
        "current_delay": 0,
        "priority": 3,
    }
    state_stopped = {
        "train_id": "12423",
        "speed_kmph": 0.0,
        "distance_remaining_km": 80.0,
        "current_delay": 0,
        "priority": 3,
    }

    res_moving = ml.predict_dynamic_eta(state_moving)
    res_stopped = ml.predict_dynamic_eta(state_stopped)

    # Stopped train must have higher predicted remaining time due to dwell penalty
    assert res_stopped["predicted_remaining_travel_time"] > res_moving["predicted_remaining_travel_time"]


# ===========================================================================
# 7. FASTAPI API ENDPOINTS INTEGRATION
# ===========================================================================

def test_api_eta_model_performance(client):
    """Verify GET /api/trains/eta/model-performance returns multi-model metrics."""
    response = client.get("/api/trains/eta/model-performance")
    assert response.status_code == 200, response.text
    data = response.json()

    assert "best_individual_model" in data
    assert "selected_production_model" in data
    assert "models" in data
    assert "ensemble_weights" in data
    assert "dataset_hash" in data
    assert data["dataset_hash"] == "d425e261dba8b6b1"


def test_api_predict_eta_with_model_selection(client):
    """Verify GET /api/trains/eta/predict supports selecting individual models and ensemble."""
    # 1. Best model (Ensemble)
    resp_best = client.get("/api/trains/eta/predict?train_number=22436&model_name=best_model")
    assert resp_best.status_code == 200
    assert resp_best.json()["model_used"] in ["Ensemble", "Random Forest", "XGBoost"]

    # 2. XGBoost
    resp_xgb = client.get("/api/trains/eta/predict?train_number=22436&model_name=xgboost")
    assert resp_xgb.status_code == 200
    assert resp_xgb.json()["model_used"] == "XGBoost"

    # 3. Random Forest
    resp_rf = client.get("/api/trains/eta/predict?train_number=22436&model_name=random_forest")
    assert resp_rf.status_code == 200
    assert resp_rf.json()["model_used"] == "Random Forest"
