"""Focused tests for weather, platform, and combined scheduling intelligence."""

from backend.schemas.api_models import (
    BlockOptimizationRequest,
    TrainDetails,
    TrainDirectionEnum,
    TrainStatusEnum,
)
from backend.services.optimizer_service import solve_maintenance_block
from backend.services.platform_service import detect_platform_conflicts
from backend.services.weather_service import calculate_weather_risk_score


def make_train(number: str, platform: int, arrival: str, departure: str) -> TrainDetails:
    return TrainDetails(
        train_number=number,
        name=f"Train {number}",
        priority=3,
        entry_min=600,
        exit_min=660,
        entry_time="10:00",
        exit_time="11:00",
        position_km=410.0,
        speed_kmph=80.0,
        direction=TrainDirectionEnum.UP,
        status=TrainStatusEnum.ON_TIME,
        platform_number=platform,
        platform_status="ASSIGNED",
        platform_available_from=arrival,
        platform_available_until=departure,
    )


def test_weather_risk_escalates_for_severe_conditions():
    risk, score, reason = calculate_weather_risk_score(90, 20.0, 65.0, 0.4)
    assert risk.value == "EXTREME"
    assert score >= 80
    assert "Extreme weather" in reason


def test_platform_availability_detects_overlapping_assignments():
    conflicts = detect_platform_conflicts([
        make_train("A", 2, "10:00", "11:30"),
        make_train("B", 2, "11:00", "12:00"),
        make_train("C", 3, "11:00", "12:00"),
    ])
    assert len(conflicts) == 1
    assert conflicts[0].platform_number == 2
    assert conflicts[0].overlap_minutes == 30


def test_maintenance_selection_reports_weather_and_platform_impact():
    request = BlockOptimizationRequest(
        duration_minutes=120,
        earliest_start_min=600,
        latest_end_min=900,
        override_weather_risk="HIGH",
        override_platform_conflict=True,
    )
    response = solve_maintenance_block(request)
    assert response.status == "OPTIMAL_SCHEDULED"
    assert response.weather_risk == "HIGH"
    assert response.safety_buffer_minutes == 10
    assert response.platform_conflicts == 1
    assert response.weighted_cost is not None
    assert response.optimization_reason


def test_normal_maintenance_window_remains_cp_sat_scheduled():
    response = solve_maintenance_block(BlockOptimizationRequest(
        duration_minutes=120,
        earliest_start_min=600,
        latest_end_min=900,
        override_weather_risk="LOW",
    ))
    assert response.status == "OPTIMAL_SCHEDULED"
    assert response.allocated_end_min - response.allocated_start_min == 120
    assert response.safety_buffer_minutes == 5


def test_trained_ml_delay_and_congestion_inference():
    from backend.services import ml_prediction_service as ml
    info = ml.get_model_info()
    assert info["status"] == "LOADED"
    assert "IR-XGB-DelayPredictor" in info["model_version"] or "IR-MultiModel" in info["model_version"] or "IR-" in info["model_version"]
    assert info["congestion_accuracy"] >= 0.90

    # Test delay inference
    pred_delay = ml.predict_delay_minutes("22436", speed_kmph=112.0, current_delay=0, priority=2)
    assert isinstance(pred_delay, int)
    assert pred_delay >= 0

    # Test congestion inference
    congestion = ml.predict_congestion(priority=2, speed_kmph=112.0, weather_risk="LOW")
    assert congestion in ("LOW", "MEDIUM", "HIGH")