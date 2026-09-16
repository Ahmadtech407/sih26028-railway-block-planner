"""
Feature Engineering for Dynamic Train ETA & Delay Prediction
============================================================
Provides unified, robust feature extraction and imputation for:
1. Model training pipeline (backend.ml.train_delay_model)
2. Real-time inference services (backend.services.ml_prediction_service)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

FEATURES_NUM = [
    "priority",
    "StationOrder",
    "halt_time_minutes",
    "distance_travelled_km",
    "distance_remaining_km",
    "speed_kmph",
    "hour_of_day",
    "is_peak_hour",
    "is_weekend",
    "temperature_c",
    "rainfall_intensity_mmh",
    "visibility_km",
    "weather_risk_score",
    "trains_in_section",
    "preceding_delay_minutes",
]

FEATURES_CAT = [
    "TrainType",
    "DayOfWeek",
    "Weather",
]


def _safe_float(val: Any, default: float) -> float:
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int) -> int:
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return default
        return int(round(float(val)))
    except (ValueError, TypeError):
        return default


def _safe_str(val: Any, default: str) -> str:
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default


def create_eta_features(train_state: Dict[str, Any]) -> pd.DataFrame:
    """
    Extract, validate, and normalize feature vector from any train state dictionary.
    Handles missing keys, None values, and alternative naming conventions safely.

    Key mappings supported:
    - distance_remaining / distance_remaining_km
    - distance_travelled / distance_travelled_km / position_km
    - current_speed / speed_kmph / speed
    - current_delay / delay_minutes / preceding_delay_minutes
    - stop_count_remaining / StationOrder
    - weather_impact_score / weather_risk_score / weather_risk
    - track_congestion_level / congestion_level
    - train_type / TrainType / train_category
    - priority
    """
    if not isinstance(train_state, dict):
        train_state = {}

    now = datetime.now(timezone.utc)

    # 1. Temporal features
    hour = train_state.get("hour_of_day")
    if hour is None:
        hour = train_state.get("hour", now.hour)
    hour = _safe_int(hour, now.hour) % 24

    day_of_week = _safe_str(train_state.get("day_of_week") or train_state.get("DayOfWeek"), now.strftime("%A"))
    is_weekend = 1 if day_of_week in ("Saturday", "Sunday") else 0
    is_peak = 1 if (6 <= hour <= 10) or (17 <= hour <= 21) else 0

    # 2. Kinematic & spatial features
    speed = train_state.get("current_speed")
    if speed is None:
        speed = train_state.get("speed_kmph", train_state.get("speed", 80.0))
    speed = max(0.0, _safe_float(speed, 80.0))

    dist_rem = train_state.get("distance_remaining")
    if dist_rem is None:
        dist_rem = train_state.get("distance_remaining_km", 322.5)
    dist_rem = max(0.0, _safe_float(dist_rem, 322.5))

    dist_trav = train_state.get("distance_travelled")
    if dist_trav is None:
        dist_trav = train_state.get("distance_travelled_km", train_state.get("position_km", 120.0))
    dist_trav = max(0.0, _safe_float(dist_trav, 120.0))

    halt_time = _safe_float(train_state.get("halt_time_minutes", train_state.get("station_dwell_time", 5.0)), 5.0)
    station_order = _safe_int(train_state.get("stop_count_remaining", train_state.get("StationOrder", 2)), 2)

    # 3. Operational priority & type
    priority = _safe_int(train_state.get("priority", 3), 3)
    train_type = train_state.get("train_type") or train_state.get("TrainType")
    if not train_type:
        if priority <= 2:
            train_type = "Superfast"
        elif priority == 3:
            train_type = "Express"
        elif priority == 4:
            train_type = "Passenger"
        else:
            train_type = "Freight"
    else:
        train_type = str(train_type).capitalize()

    # 4. Weather impact
    w_raw = _safe_str(train_state.get("Weather") or train_state.get("weather_risk") or train_state.get("weather"), "Clear")
    w_upper = w_raw.upper()
    w_score = train_state.get("weather_impact_score") or train_state.get("weather_risk_score")

    if "THUNDER" in w_upper or "EXTREME" in w_upper:
        weather_desc = "Thunderstorm"
        weather_score = 90.0 if w_score is None else _safe_float(w_score, 90.0)
        rain_mmh = 18.0
        vis_km = 1.0
    elif "RAIN" in w_upper or "HIGH" in w_upper:
        weather_desc = "Rainy"
        weather_score = 65.0 if w_score is None else _safe_float(w_score, 65.0)
        rain_mmh = 6.0
        vis_km = 2.0
    elif "CLOUD" in w_upper or "FOG" in w_upper or "MEDIUM" in w_upper:
        weather_desc = "Cloudy"
        weather_score = 35.0 if w_score is None else _safe_float(w_score, 35.0)
        rain_mmh = 1.0
        vis_km = 5.0
    else:
        weather_desc = "Clear"
        weather_score = 10.0 if w_score is None else _safe_float(w_score, 10.0)
        rain_mmh = 0.0
        vis_km = 9.0

    temp_c = _safe_float(train_state.get("temperature_c", 28.0), 28.0)

    # 5. Congestion & track load
    cong_raw = _safe_str(train_state.get("track_congestion_level") or train_state.get("congestion_level"), "LOW").upper()
    if "HIGH" in cong_raw:
        trains_in_sec = 4
    elif "MEDIUM" in cong_raw:
        trains_in_sec = 2
    else:
        trains_in_sec = _safe_int(train_state.get("trains_in_section", 1), 1)

    # 6. Current delay
    curr_delay = train_state.get("current_delay")
    if curr_delay is None:
        curr_delay = train_state.get("delay_minutes", train_state.get("preceding_delay_minutes", 0.0))
    curr_delay = max(0.0, _safe_float(curr_delay, 0.0))

    row = {
        "priority": priority,
        "StationOrder": station_order,
        "halt_time_minutes": halt_time,
        "distance_travelled_km": dist_trav,
        "distance_remaining_km": dist_rem,
        "speed_kmph": speed,
        "hour_of_day": hour,
        "is_peak_hour": is_peak,
        "is_weekend": is_weekend,
        "temperature_c": temp_c,
        "rainfall_intensity_mmh": rain_mmh,
        "visibility_km": vis_km,
        "weather_risk_score": weather_score,
        "trains_in_section": trains_in_sec,
        "preceding_delay_minutes": curr_delay,
        "TrainType": train_type,
        "DayOfWeek": day_of_week,
        "Weather": weather_desc,
    }

    return pd.DataFrame([row])
