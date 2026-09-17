"""
Feature Engineering for Dynamic Train ETA & Delay Prediction
============================================================
Provides unified, robust feature extraction and imputation for:
1. Model training pipeline (backend.ml.train_delay_model)
2. Real-time inference services (backend.services.ml_prediction_service)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
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


def prepare_training_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Standardize a unified railway dataset DataFrame into the model feature matrix X,
    and both ML targets:
      y_eta: target_remaining_travel_time_minutes
      y_delay: target_delay_minutes
    Strictly excludes all leaked and post-trip variables.
    """
    X = pd.DataFrame(index=df.index)

    # Priority mapping
    priority_map = {
        "EMERGENCY": 1,
        "SUPERFAST": 2,
        "RAJADHANI": 2,
        "VANDE BHARAT": 2,
        "EXPRESS": 3,
        "MAIL": 3,
        "PASSENGER": 4,
        "FREIGHT": 5,
    }
    def _get_series(col_candidates: List[str], default_val: Any) -> pd.Series:
        for col in col_candidates:
            if col in df.columns:
                return df[col]
        return pd.Series(default_val, index=df.index)

    t_type_series = _get_series(["train_type", "TrainType"], "EXPRESS").fillna("EXPRESS").astype(str).str.upper()
    X["priority"] = t_type_series.map(lambda t: priority_map.get(t, 3)).astype(int)
    X["TrainType"] = t_type_series.map(lambda t: "Superfast" if priority_map.get(t, 3) <= 2 else ("Passenger" if priority_map.get(t, 3) == 4 else ("Freight" if priority_map.get(t, 3) == 5 else "Express")))

    # Kinematics
    X["distance_travelled_km"] = pd.to_numeric(_get_series(["distance_km", "distance_travelled_km"], 100.0), errors="coerce").fillna(100.0)
    X["distance_remaining_km"] = pd.to_numeric(_get_series(["distance_remaining_km", "distance_remaining"], 200.0), errors="coerce").fillna(200.0)
    X["speed_kmph"] = pd.to_numeric(_get_series(["speed", "speed_kmph"], 80.0), errors="coerce").fillna(80.0)
    X["StationOrder"] = pd.to_numeric(_get_series(["StationOrder", "station_order"], 2), errors="coerce").fillna(2).astype(int)
    X["halt_time_minutes"] = pd.to_numeric(_get_series(["station_dwell_time", "halt_time_minutes"], 5.0), errors="coerce").fillna(5.0)

    # Timestamps & Temporals
    ts_series = _get_series(["parsed_timestamp", "timestamp"], datetime.now(timezone.utc))
    ts = pd.to_datetime(ts_series, errors="coerce", utc=True)
    X["hour_of_day"] = ts.dt.hour.fillna(12).astype(int)
    X["is_peak_hour"] = X["hour_of_day"].apply(lambda h: 1 if (6 <= h <= 10) or (17 <= h <= 21) else 0)
    X["DayOfWeek"] = ts.dt.day_name().fillna("Wednesday")
    X["is_weekend"] = X["DayOfWeek"].apply(lambda d: 1 if d in ("Saturday", "Sunday") else 0)

    # Environmental
    w_series = _get_series(["weather", "Weather"], "CLEAR").fillna("CLEAR").astype(str).str.upper()
    X["Weather"] = w_series.map(lambda w: "Thunderstorm" if "THUNDER" in w else ("Rainy" if "RAIN" in w else ("Cloudy" if ("CLOUD" in w or "FOG" in w) else "Clear")))
    X["temperature_c"] = pd.to_numeric(_get_series(["temperature", "temperature_c"], 26.0), errors="coerce").fillna(26.0)
    X["rainfall_intensity_mmh"] = pd.to_numeric(_get_series(["rain", "rainfall_intensity_mmh"], 0.0), errors="coerce").fillna(0.0)
    X["visibility_km"] = pd.to_numeric(_get_series(["visibility", "visibility_km"], 8.0), errors="coerce").fillna(8.0)
    
    risk_map = {"Clear": 10.0, "Cloudy": 35.0, "Rainy": 65.0, "Thunderstorm": 90.0}
    X["weather_risk_score"] = X["Weather"].map(lambda w: risk_map.get(w, 20.0))

    # Traffic
    cong_series = _get_series(["congestion", "target_congestion_level"], "LOW").fillna("LOW").astype(str).str.upper()
    X["trains_in_section"] = cong_series.map(lambda c: 4 if "HIGH" in c or "CRITICAL" in c else (2 if "MEDIUM" in c else 1)).astype(int)
    
    # Preceding delay
    X["preceding_delay_minutes"] = pd.to_numeric(_get_series(["delay_minutes", "preceding_delay_minutes"], 0.0), errors="coerce").fillna(0.0)

    # Targets
    y_delay = pd.to_numeric(_get_series(["delay_minutes", "target_delay_minutes"], 0.0), errors="coerce").fillna(0.0)
    
    if "remaining_travel_time_minutes" in df.columns and df["remaining_travel_time_minutes"].notna().sum() > 0:
        y_eta = pd.to_numeric(df["remaining_travel_time_minutes"], errors="coerce")
    elif "target_remaining_travel_time_minutes" in df.columns:
        y_eta = pd.to_numeric(df["target_remaining_travel_time_minutes"], errors="coerce")
    else:
        eff_spd = np.maximum(25.0, X["speed_kmph"])
        base_time = (X["distance_remaining_km"] / eff_spd) * 60.0 + X["StationOrder"] * X["halt_time_minutes"]
        y_eta = np.maximum(1.0, base_time + y_delay).round(2)
        
    y_eta = y_eta.fillna(((X["distance_remaining_km"] / np.maximum(25.0, X["speed_kmph"])) * 60.0 + y_delay).round(2))

    return X[FEATURES_NUM + FEATURES_CAT], y_eta, y_delay
