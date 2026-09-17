"""
Railway Data Quality & Temporal Splitting Pipeline
===================================================
1. Cleans and audits the unified dataset:
   - Deduplication
   - Strict timestamp parsing and validation
   - Physical constraints (speed <= 160 km/h, distance >= 0, delay >= -30 min)
   - Impossible travel time detection (t >= d / 160 km/h)
   - Outlier screening
   - Controlled missing value imputation
2. Emits comprehensive Data Quality Audit Report (metadata/data_quality_report.json)
3. Executes strictly Chronological Train / Validation / Test Splitting (70% / 15% / 15%)
   to eliminate lookahead bias, saving:
   - processed/train_split.csv
   - processed/val_split.csv
   - processed/test_split.csv
   - metadata/split_metadata.json
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, List

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "backend" / "ml" / "data"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"


def run_data_quality_pipeline() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Execute quality filters, clean data, and save report."""
    input_csv = PROCESSED_DIR / "unified_railway_dataset.csv"
    if not input_csv.exists():
        from backend.ml.data.ingest_pipeline import build_unified_dataset
        build_unified_dataset()

    df_raw = pd.read_csv(input_csv)
    records_loaded = len(df_raw)
    logger.info("Quality Pipeline loaded %d records", records_loaded)

    # Missing values snapshot
    missing_before = df_raw.isna().sum().to_dict()

    # 1. Deduplication
    dup_mask = df_raw.duplicated(subset=["train_number", "distance_km", "timestamp", "delay_minutes"], keep="first")
    duplicates_count = int(dup_mask.sum())
    df_clean = df_raw[~dup_mask].copy()

    # 2. Timestamp validation and chronological parsing
    def safe_parse_dt(val):
        try:
            return pd.to_datetime(val, utc=True)
        except Exception:
            return pd.NaT

    df_clean["parsed_timestamp"] = df_clean["timestamp"].apply(safe_parse_dt)
    corrupted_timestamps = int(df_clean["parsed_timestamp"].isna().sum())
    df_clean = df_clean[df_clean["parsed_timestamp"].notna()].copy()

    # 3. Physical feasibility & boundary validation
    invalid_speed_count = 0
    invalid_time_count = 0
    invalid_delay_count = 0
    outlier_count = 0

    valid_mask = pd.Series(True, index=df_clean.index)

    # Check speeds
    speed_numeric = pd.to_numeric(df_clean["speed"], errors="coerce")
    bad_speed = (speed_numeric < 0) | (speed_numeric > 160.0)
    invalid_speed_count = int(bad_speed.fillna(False).sum())
    valid_mask = valid_mask & (~bad_speed.fillna(False))

    # Check delays
    delay_numeric = pd.to_numeric(df_clean["delay_minutes"], errors="coerce")
    bad_delay = (delay_numeric < -30.0) | (delay_numeric > 1440.0)
    invalid_delay_count = int(bad_delay.fillna(False).sum())
    valid_mask = valid_mask & (~bad_delay.fillna(False))

    # Check remaining distances and travel times
    dist_rem_numeric = pd.to_numeric(df_clean["distance_remaining_km"], errors="coerce")
    rem_time_numeric = pd.to_numeric(df_clean["remaining_travel_time_minutes"], errors="coerce")
    
    # Impossible speed test: if remaining distance / remaining travel time > 180 km/h
    with np.errstate(divide="ignore", invalid="ignore"):
        implied_speed = (dist_rem_numeric / np.maximum(1.0, rem_time_numeric)) * 60.0
        impossible_kinematics = implied_speed > 160.0
        invalid_time_count = int(impossible_kinematics.fillna(False).sum())
        valid_mask = valid_mask & (~impossible_kinematics.fillna(False))

    # Outlier detection via IQR on delay
    q25 = delay_numeric.quantile(0.25)
    q75 = delay_numeric.quantile(0.75)
    iqr = q75 - q25
    delay_outliers = (delay_numeric > (q75 + 4.0 * iqr)) & (delay_numeric > 240.0)
    outlier_count = int(delay_outliers.fillna(False).sum())
    valid_mask = valid_mask & (~delay_outliers.fillna(False))

    invalid_records = invalid_speed_count + invalid_time_count + invalid_delay_count + corrupted_timestamps
    records_removed = duplicates_count + (len(df_clean) - int(valid_mask.sum()))

    df_valid = df_clean[valid_mask].copy()
    records_valid = len(df_valid)

    # 4. Contextual domain imputation for remaining modeling features
    # Ensure remaining travel time and delay are present for rows used in training
    df_valid["distance_remaining_km"] = df_valid["distance_remaining_km"].fillna(
        pd.to_numeric(df_valid["distance_km"], errors="coerce").apply(lambda d: max(15.0, 500.0 - float(d or 100.0)))
    )
    df_valid["speed"] = pd.to_numeric(df_valid["speed"], errors="coerce").fillna(85.0)
    df_valid["delay_minutes"] = pd.to_numeric(df_valid["delay_minutes"], errors="coerce").fillna(0.0)
    
    # Calculate genuine physical lower-bound remaining travel time if missing
    eff_spd = np.maximum(25.0, df_valid["speed"])
    df_valid["remaining_travel_time_minutes"] = df_valid["remaining_travel_time_minutes"].fillna(
        ((df_valid["distance_remaining_km"] / eff_spd) * 60.0 + df_valid["delay_minutes"]).round(1)
    )

    # Impute environmental and traffic features safely
    df_valid["weather"] = df_valid["weather"].fillna("CLEAR")
    df_valid["temperature"] = pd.to_numeric(df_valid["temperature"], errors="coerce").fillna(25.0)
    df_valid["rain"] = pd.to_numeric(df_valid["rain"], errors="coerce").fillna(0.0)
    df_valid["visibility"] = pd.to_numeric(df_valid["visibility"], errors="coerce").fillna(8.0)
    df_valid["congestion"] = df_valid["congestion"].fillna("LOW")
    df_valid["station_dwell_time"] = pd.to_numeric(df_valid["station_dwell_time"], errors="coerce").fillna(5.0)
    df_valid["disruption"] = df_valid["disruption"].fillna("NONE")
    df_valid["train_type"] = df_valid["train_type"].fillna("EXPRESS")

    final_training_rows = len(df_valid)

    quality_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_loaded": records_loaded,
        "records_removed": records_removed,
        "records_valid": records_valid,
        "missing_values_initial": missing_before,
        "duplicates": duplicates_count,
        "corrupted_timestamps": corrupted_timestamps,
        "invalid_speeds": invalid_speed_count,
        "impossible_travel_times": invalid_time_count,
        "invalid_delays": invalid_delay_count,
        "outliers": outlier_count,
        "invalid_records": invalid_records,
        "final_training_rows": final_training_rows,
    }

    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    report_file = METADATA_DIR / "data_quality_report.json"
    report_file.write_text(json.dumps(quality_report, indent=2), encoding="utf-8")
    logger.info("Saved data quality report -> %s", report_file)

    return df_valid, quality_report


def split_chronologically(df: pd.DataFrame, train_pct: float = 0.70, val_pct: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Split dataset chronologically into Train (70%), Validation (15%), and Test (15%).
    Never shuffles randomly to prevent temporal lookahead bias.
    """
    df_sorted = df.sort_values(by="parsed_timestamp").reset_index(drop=True)
    n = len(df_sorted)
    
    n_train = int(n * train_pct)
    n_val = int(n * val_pct)
    
    train_df = df_sorted.iloc[:n_train].copy()
    val_df = df_sorted.iloc[n_train:n_train + n_val].copy()
    test_df = df_sorted.iloc[n_train + n_val:].copy()

    split_metadata = {
        "split_method": "STRICT_CHRONOLOGICAL_TEMPORAL",
        "total_rows": n,
        "train_rows": len(train_df),
        "val_rows": len(val_df),
        "test_rows": len(test_df),
        "train_date_range": [
            str(train_df["parsed_timestamp"].min().date()),
            str(train_df["parsed_timestamp"].max().date()),
        ],
        "val_date_range": [
            str(val_df["parsed_timestamp"].min().date()),
            str(val_df["parsed_timestamp"].max().date()),
        ],
        "test_date_range": [
            str(test_df["parsed_timestamp"].min().date()),
            str(test_df["parsed_timestamp"].max().date()),
        ],
    }

    # Save to processed directory
    train_path = PROCESSED_DIR / "train_split.csv"
    val_path = PROCESSED_DIR / "val_split.csv"
    test_path = PROCESSED_DIR / "test_split.csv"
    meta_path = METADATA_DIR / "split_metadata.json"

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)
    meta_path.write_text(json.dumps(split_metadata, indent=2), encoding="utf-8")

    logger.info("Chronological split completed: Train=%d, Val=%d, Test=%d", len(train_df), len(val_df), len(test_df))
    logger.info("Train dates: %s to %s", split_metadata["train_date_range"][0], split_metadata["train_date_range"][1])
    logger.info("Val dates:   %s to %s", split_metadata["val_date_range"][0], split_metadata["val_date_range"][1])
    logger.info("Test dates:  %s to %s", split_metadata["test_date_range"][0], split_metadata["test_date_range"][1])

    return train_df, val_df, test_df, split_metadata


class RailwayDataQualityPipeline:
    """Class wrapper for railway data validation, cleaning, and quality auditing."""

    def clean_and_audit(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        df_clean = df.copy()

        # 1. Deduplication
        dup_cols = [c for c in ["train_number", "distance_km", "timestamp", "delay_minutes"] if c in df_clean.columns]
        if dup_cols:
            df_clean = df_clean.drop_duplicates(subset=dup_cols, keep="first")

        # 2. Timestamp parsing
        if "timestamp" in df_clean.columns:
            df_clean["parsed_timestamp"] = pd.to_datetime(df_clean["timestamp"], errors="coerce", utc=True)
            df_clean = df_clean[df_clean["parsed_timestamp"].notna()].copy()

        # 3. Physical boundaries
        valid_mask = pd.Series(True, index=df_clean.index)

        # Distance >= 0
        dist_col = "distance_km" if "distance_km" in df_clean.columns else ("distance_remaining_km" if "distance_remaining_km" in df_clean.columns else None)
        if dist_col:
            d_val = pd.to_numeric(df_clean[dist_col], errors="coerce")
            valid_mask = valid_mask & (d_val >= 0.0)

        # Speed [0, 160]
        speed_col = "speed" if "speed" in df_clean.columns else ("speed_kmph" if "speed_kmph" in df_clean.columns else None)
        if speed_col:
            s_val = pd.to_numeric(df_clean[speed_col], errors="coerce")
            valid_mask = valid_mask & (s_val >= 0.0) & (s_val <= 160.0)

        # Delay [-30, 1440]
        delay_col = "delay_minutes" if "delay_minutes" in df_clean.columns else ("target_delay_minutes" if "target_delay_minutes" in df_clean.columns else None)
        if delay_col:
            del_val = pd.to_numeric(df_clean[delay_col], errors="coerce")
            valid_mask = valid_mask & (del_val >= -30.0) & (del_val <= 1440.0)

        # Impossible travel time (speed implied by distance / time cannot exceed 160 km/h)
        time_col = "scheduled_travel_time" if "scheduled_travel_time" in df_clean.columns else ("remaining_travel_time_minutes" if "remaining_travel_time_minutes" in df_clean.columns else None)
        if dist_col and time_col:
            d_series = pd.to_numeric(df_clean[dist_col], errors="coerce")
            t_series = pd.to_numeric(df_clean[time_col], errors="coerce")
            implied_spd = (d_series / np.maximum(0.1, t_series)) * 60.0
            valid_mask = valid_mask & (implied_spd <= 160.0)

        cleaned_df = df_clean[valid_mask].copy()
        report = {
            "records_in": len(df),
            "records_valid": len(cleaned_df),
            "records_removed": len(df) - len(cleaned_df),
        }
        return cleaned_df, report

    def run(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        return run_data_quality_pipeline()

    def split(self, df: pd.DataFrame):
        return split_chronologically(df)


if __name__ == "__main__":
    clean_df, q_rep = run_data_quality_pipeline()
    tr, val, ts, s_meta = split_chronologically(clean_df)
    print("Quality Report Summary:")
    print(json.dumps(q_rep, indent=2))
    print("Split Metadata:")
    print(json.dumps(s_meta, indent=2))
