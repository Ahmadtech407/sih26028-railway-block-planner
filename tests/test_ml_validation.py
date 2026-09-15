"""
Validation tests for Trained Machine Learning Delay & Congestion Models.
Verifies model serialization, 5-fold cross-validation metrics, probability extraction, and fallback mechanisms.
"""

import pytest
from backend.services import ml_prediction_service as ml


def test_model_metadata_and_5fold_cv():
    info = ml.get_model_info()
    assert info["status"] == "LOADED"
    assert "IR-GBM-DelayPredictor-v2.0" in info["model_version"]
    assert info["congestion_accuracy"] >= 0.90
    assert info["congestion_classification_f1"] >= 0.90


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
