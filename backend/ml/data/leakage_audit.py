"""
Feature Leakage Prevention & Audit Engine
==========================================
Audits and guarantees zero temporal lookahead bias or post-trip leakage
in the RailTrack machine learning prediction pipelines.

Features must strictly belong to SAFE_FEATURES (observable at the prediction moment).
Post-trip outcomes (actual arrival, final trip delay, delay reasons) are barred.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 1. Strictly observable before or at the moment of prediction
SAFE_FEATURES = {
    # Train attributes
    "train_number",
    "train_id",
    "TrainID",
    "train_type",
    "TrainType",
    "priority",
    # Kinematic & spatial parameters known at current position
    "distance_km",
    "distance_travelled_km",
    "distance_remaining_km",
    "speed",
    "speed_kmph",
    "StationOrder",
    "station_order",
    "halt_time_minutes",
    "scheduled_dwell_time",
    "track_gradient_pct",
    "train_mass_tonnes",
    # Preceding temporal & delay observations
    "current_delay",
    "preceding_delay_minutes",
    "scheduled_travel_time",
    "scheduled_arrival",
    "scheduled_departure",
    "dep_minutes",
    # Ambient environmental conditions at prediction time
    "weather",
    "Weather",
    "weather_risk",
    "weather_risk_score",
    "temperature",
    "temperature_c",
    "rain",
    "rainfall_intensity_mmh",
    "visibility",
    "visibility_km",
    # Traffic & operational state at prediction time
    "congestion",
    "congestion_level",
    "trains_in_section",
    "hour_of_day",
    "is_peak_hour",
    "day_of_week",
    "DayOfWeek",
    "is_weekend",
    "data_source",
    "section_id",
    "source_station",
    "destination_station",
}

# 2. Features that require validation of observation timestamp
SUSPICIOUS_FEATURES = {
    "station_dwell_time",
    "actual_departure",       # Only safe if from PREVIOUS completed station
    "disruption",             # Safe if currently active; unsafe if post-incident classification
    "delay_minutes",          # Unsafe if destination delay; safe if preceding station delay
}

# 3. Post-trip ground truth / lookahead features (STRICTLY FORBIDDEN IN FEATURE MATRIX)
LEAKED_FEATURES = {
    "actual_arrival",
    "ActualArrival",
    "actual_departure_destination",
    "actual_travel_time",
    "final_delay",
    "target_delay_minutes",
    "target_remaining_travel_time_minutes",
    "target_congestion_level",
    "delay_reason",
    "DelayReason",
    "future_station_delay",
    "post_trip_cause",
    "future_weather",
    "future_congestion",
}


def audit_features(feature_names: List[str]) -> Dict[str, Any]:
    """
    Audit an iterable of feature column names.
    Categorizes each feature into safe, suspicious, or leaked.
    """
    safe_list = []
    suspicious_list = []
    leaked_list = []
    unknown_list = []

    for feat in feature_names:
        clean_name = feat.strip()
        lower_name = clean_name.lower()
        
        # Check explicit leaked
        if clean_name in LEAKED_FEATURES or any(clean_name == l for l in LEAKED_FEATURES):
            leaked_list.append(clean_name)
        elif "actual" in lower_name and "preceding" not in lower_name:
            leaked_list.append(clean_name)
        elif "target" in lower_name:
            leaked_list.append(clean_name)
        elif "final" in lower_name:
            leaked_list.append(clean_name)
        elif clean_name in SAFE_FEATURES:
            safe_list.append(clean_name)
        elif clean_name in SUSPICIOUS_FEATURES:
            suspicious_list.append(clean_name)
        else:
            unknown_list.append(clean_name)

    is_clean = len(leaked_list) == 0

    return {
        "is_leak_free": is_clean,
        "total_features_audited": len(feature_names),
        "safe_features": safe_list,
        "suspicious_features": suspicious_list,
        "leaked_features": leaked_list,
        "unknown_features": unknown_list,
    }


def audit_dataframe(df: pd.DataFrame, target_cols: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Audit an entire DataFrame for data leakage and suspicious target correlations.
    """
    targets = target_cols or ["target_delay_minutes", "target_remaining_travel_time_minutes", "delay_minutes", "remaining_travel_time_minutes"]
    feature_cols = [c for c in df.columns if c not in targets]

    base_audit = audit_features(feature_cols)
    
    # Correlation audit: check for suspicious near-perfect correlation (r > 0.999) with target
    high_correlation_flags = []
    for tgt in targets:
        if tgt in df.columns and pd.api.types.is_numeric_dtype(df[tgt]):
            for col in base_audit["safe_features"]:
                if pd.api.types.is_numeric_dtype(df[col]):
                    valid_mask = df[col].notna() & df[tgt].notna()
                    if valid_mask.sum() > 20:
                        corr = np.corrcoef(df.loc[valid_mask, col], df.loc[valid_mask, tgt])[0, 1]
                        if abs(corr) > 0.999:
                            high_correlation_flags.append({
                                "feature": col,
                                "target": tgt,
                                "correlation": float(round(corr, 4)),
                                "warning": "Near-perfect correlation indicates potential algebraic target leakage."
                            })

    base_audit["high_correlation_leakage_flags"] = high_correlation_flags
    if high_correlation_flags:
        base_audit["is_leak_free"] = False

    return base_audit


def sanitize_training_matrix(df: pd.DataFrame, target_cols: Optional[List[str]] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Remove any leaked or forbidden columns from DataFrame, returning sanitized DataFrame and audit report.
    """
    targets = target_cols or ["target_delay_minutes", "target_remaining_travel_time_minutes", "delay_minutes", "remaining_travel_time_minutes"]
    audit_report = audit_dataframe(df, target_cols=targets)

    cols_to_drop = [c for c in audit_report["leaked_features"] if c in df.columns]
    sanitized_df = df.drop(columns=cols_to_drop)

    logger.info("Sanitized training DataFrame: dropped %d leaked columns: %s", len(cols_to_drop), cols_to_drop)
    return sanitized_df, audit_report


class LeakageAuditor:
    """Class wrapper for feature and dataframe leakage auditing."""

    def audit_features(self, feature_names: List[str]) -> Dict[str, Any]:
        return audit_features(feature_names)

    def audit_dataframe(
        self,
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        target_cols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        targets = [target_col] if target_col else target_cols
        return audit_dataframe(df, target_cols=targets)

    def sanitize_training_matrix(
        self,
        df: pd.DataFrame,
        target_cols: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        return sanitize_training_matrix(df, target_cols=target_cols)


if __name__ == "__main__":
    test_features = [
        "speed_kmph",
        "distance_remaining_km",
        "priority",
        "actual_arrival",
        "final_delay",
        "temperature_c",
        "preceding_delay_minutes",
    ]
    report = audit_features(test_features)
    print("Feature Check Report:")
    print(json.dumps(report, indent=2))

    train_split_file = Path(__file__).resolve().parent / "processed" / "train_split.csv"
    if train_split_file.exists():
        df_train = pd.read_csv(train_split_file)
        full_report = audit_dataframe(df_train)
        meta_file = Path(__file__).resolve().parent / "metadata" / "leakage_audit_report.json"
        meta_file.parent.mkdir(parents=True, exist_ok=True)
        meta_file.write_text(json.dumps(full_report, indent=2), encoding="utf-8")
        print(f"\nSaved Leakage Audit Report to {meta_file}:")
        print(f"Is Leak Free: {full_report['is_leak_free']}")
        print(f"Safe Features: {len(full_report['safe_features'])}")
        print(f"Leaked Features: {len(full_report['leaked_features'])} ({full_report['leaked_features']})")
