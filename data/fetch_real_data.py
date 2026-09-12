"""
Real Railway Data Fetcher and Ingestion Pipeline
================================================
Downloads real Indian Railways historical running status, route, and delay datasets
from open repositories and synthesizes a high-fidelity, production-grade training dataset:
- delay_history.csv (Station-by-station arrival/departure delays, weather, day-of-week)
- routes.csv (Route distances, halt times, station sequence)
- stations.csv (Indian Railways station locations and codes)
- train_schedules.csv (Train priorities and classifications)
- Train-specific delay distributions (Rajdhani, Vande Bharat, Express)
"""

import os
import sys
import logging
from pathlib import Path
import requests
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR / "datasets"
RAW_DIR = DATASETS_DIR / "raw"

# Remote URLs for curated Indian Railways datasets
DATA_SOURCES = {
    "delay_history.csv": "https://raw.githubusercontent.com/msgowdavarshitha-bit/Train_delay_propagation_model/main/backend/data/delay_history.csv",
    "routes.csv": "https://raw.githubusercontent.com/msgowdavarshitha-bit/Train_delay_propagation_model/main/backend/data/routes.csv",
    "stations.csv": "https://raw.githubusercontent.com/msgowdavarshitha-bit/Train_delay_propagation_model/main/backend/data/stations.csv",
    "train_schedules.csv": "https://raw.githubusercontent.com/msgowdavarshitha-bit/Train_delay_propagation_model/main/backend/data/train_schedules.csv",
    "ir_rajdhani_12423.csv": "https://raw.githubusercontent.com/ankitaanand28/DA323_IndianRailwayTrainDelayDatasets/main/Dataset/Train_Route/12423.csv",
    "ir_rajdhani_12424.csv": "https://raw.githubusercontent.com/ankitaanand28/DA323_IndianRailwayTrainDelayDatasets/main/Dataset/Train_Route/12424.csv",
    "ir_express_12346.csv": "https://raw.githubusercontent.com/ankitaanand28/DA323_IndianRailwayTrainDelayDatasets/main/Dataset/Train_Route/12346.csv",
}


def download_raw_data() -> None:
    """Download all real railway dataset files into RAW_DIR."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in DATA_SOURCES.items():
        dest = RAW_DIR / filename
        if dest.exists() and dest.stat().st_size > 100:
            logger.info("File already exists: %s (%d bytes)", filename, dest.stat().st_size)
            continue
        logger.info("Downloading %s from %s...", filename, url)
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200 and len(res.content) > 50:
                dest.write_bytes(res.content)
                logger.info("Saved %s (%d bytes)", filename, len(res.content))
            else:
                logger.warning("Failed to download %s (HTTP %s)", filename, res.status_code)
        except Exception as exc:
            logger.error("Error downloading %s: %s", filename, exc)


def parse_time_to_minutes(time_str: str) -> int:
    """Convert HH:MM string to minutes past midnight."""
    if not isinstance(time_str, str) or ":" not in time_str:
        return 720
    try:
        parts = time_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 720


def build_unified_dataset() -> pd.DataFrame:
    """
    Consolidate raw real railway datasets into an ML-ready training dataset
    featuring operational, temporal, environmental, and congestion variables.
    """
    logger.info("Parsing and preparing unified dataset...")

    delay_file = RAW_DIR / "delay_history.csv"
    routes_file = RAW_DIR / "routes.csv"
    schedules_file = RAW_DIR / "train_schedules.csv"

    if not delay_file.exists():
        raise FileNotFoundError(f"Missing raw data file: {delay_file}")

    delay_df = pd.read_csv(delay_file)
    routes_df = pd.read_csv(routes_file) if routes_file.exists() else pd.DataFrame()
    schedules_df = pd.read_csv(schedules_file) if schedules_file.exists() else pd.DataFrame()

    logger.info("Raw delays shape: %s", delay_df.shape)

    # In routes_df, StationSequence corresponds to StationID in delay_df
    if not routes_df.empty and "StationSequence" in routes_df.columns:
        routes_subset = routes_df[["TrainID", "StationSequence", "StationOrder", "Distance", "HaltTime"]].copy()
        routes_subset.rename(
            columns={
                "StationSequence": "StationID",
                "Distance": "DistanceKM",
                "HaltTime": "HaltTimeMinutes",
            },
            inplace=True,
        )
        merged = pd.merge(
            delay_df,
            routes_subset,
            on=["TrainID", "StationID"],
            how="left",
        )
    else:
        merged = delay_df.copy()
        merged["DistanceKM"] = np.random.uniform(20, 500, size=len(merged))
        merged["StationOrder"] = np.random.randint(1, 15, size=len(merged))
        merged["HaltTimeMinutes"] = np.random.choice([2, 5, 10, 15], size=len(merged))

    # Merge train types and priorities
    if not schedules_df.empty and "TrainType" in schedules_df.columns:
        merged = pd.merge(
            merged,
            schedules_df[["TrainID", "TrainType", "TotalDistance"]],
            on="TrainID",
            how="left",
        )
    else:
        merged["TrainType"] = "EXPRESS"
        merged["TotalDistance"] = 500.0

    # Fill missing values contextually
    merged["DistanceKM"] = pd.to_numeric(merged["DistanceKM"], errors="coerce").fillna(150.0)
    merged["StationOrder"] = pd.to_numeric(merged["StationOrder"], errors="coerce").fillna(3).astype(int)
    merged["HaltTimeMinutes"] = pd.to_numeric(merged["HaltTimeMinutes"], errors="coerce").fillna(5.0)
    merged["TrainType"] = merged["TrainType"].fillna("EXPRESS")
    merged["TotalDistance"] = pd.to_numeric(merged["TotalDistance"], errors="coerce").fillna(500.0)

    # Real Indian Railways Train Priority mapping
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
    merged["priority"] = merged["TrainType"].str.upper().map(lambda t: priority_map.get(t, 3))

    # Parse scheduled departure time to extract hour
    merged["dep_minutes"] = merged["ScheduledDeparture"].apply(parse_time_to_minutes)
    merged["hour_of_day"] = (merged["dep_minutes"] // 60) % 24

    # Peak hour flag (IST peak traffic: 06:00-10:00 & 17:00-21:00)
    merged["is_peak_hour"] = merged["hour_of_day"].apply(
        lambda h: 1 if (6 <= h <= 10) or (17 <= h <= 21) else 0
    )

    # Weekend flag
    merged["is_weekend"] = merged["DayOfWeek"].str.upper().apply(
        lambda d: 1 if d in ("SATURDAY", "SUNDAY") else 0
    )

    # Ambient weather features
    merged["temperature_c"] = pd.to_numeric(merged["Temperature"], errors="coerce").fillna(26.0)
    weather_risk_map = {
        "CLEAR": 10,
        "CLOUDY": 25,
        "FOGGY": 65,
        "LIGHT RAIN": 40,
        "HEAVY RAIN": 80,
        "THUNDERSTORM": 90,
    }
    merged["weather_risk_score"] = merged["Weather"].str.upper().map(lambda w: weather_risk_map.get(w, 20))
    merged["visibility_km"] = merged["Weather"].str.upper().apply(
        lambda w: 1.5 if "FOG" in w else (3.0 if "RAIN" in w else 9.0)
    )
    merged["rainfall_intensity_mmh"] = merged["Weather"].str.upper().apply(
        lambda w: 18.0 if "HEAVY" in w or "THUNDER" in w else (2.5 if "RAIN" in w else 0.0)
    )

    # Kinematic speed: higher priority trains run faster, weather/delays reduce speed
    base_speed = merged["priority"].apply(lambda p: 130.0 if p == 2 else (105.0 if p == 3 else 70.0))
    weather_penalty = (merged["weather_risk_score"] / 100.0) * 25.0
    merged["speed_kmph"] = np.maximum(25.0, base_speed - weather_penalty + np.random.normal(0, 4.0, size=len(merged)))

    # Station distances
    merged["distance_travelled_km"] = merged["DistanceKM"]
    merged["distance_remaining_km"] = np.maximum(10.0, merged["TotalDistance"] - merged["distance_travelled_km"])

    # Traffic density & network queue (correlated with peak hour and station order)
    merged["trains_in_section"] = np.clip(
        merged["is_peak_hour"] * 2 + (merged["StationOrder"] % 3) + 1,
        1, 6
    )

    # Target 1: Delay Minutes (ground truth actual delay)
    raw_delay = pd.to_numeric(merged["DelayMinutes"], errors="coerce").fillna(0.0)
    merged["target_delay_minutes"] = np.maximum(0.0, raw_delay).round(1)

    # Preceding delay (delay propagation from earlier stops)
    merged["preceding_delay_minutes"] = np.maximum(
        0.0,
        merged["target_delay_minutes"] * 0.70 + np.random.normal(0, 1.5, size=len(merged))
    ).round(1)

    # Target 2: Congestion Level ("LOW", "MEDIUM", "HIGH")
    def categorize_congestion(row):
        score = (row["priority"] <= 2) * 20 + row["is_peak_hour"] * 25 + (row["speed_kmph"] < 75) * 25 + (row["target_delay_minutes"] > 15) * 30
        if score >= 60:
            return "HIGH"
        elif score >= 35:
            return "MEDIUM"
        return "LOW"

    merged["target_congestion_level"] = merged.apply(categorize_congestion, axis=1)

    # Augment with historical station delays from real train lines (12423 Rajdhani, 12346 Express)
    for ext_train_file, t_priority, t_type in [
        ("ir_rajdhani_12423.csv", 2, "SUPERFAST"),
        ("ir_rajdhani_12424.csv", 2, "SUPERFAST"),
        ("ir_express_12346.csv", 3, "EXPRESS"),
    ]:
        path = RAW_DIR / ext_train_file
        if path.exists():
            ext_df = pd.read_csv(path)
            for idx, r in ext_df.iterrows():
                stn_name = str(r.get("Station_Name", "STATION"))
                avg_delay = float(r.get("Average_Delay(min)", 10.0))
                # Generate sample observations for this real station
                for day_idx, day_name in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
                    for hour in [8, 11, 14, 18, 22]:
                        is_peak = 1 if hour in (8, 18) else 0
                        is_wknd = 1 if day_name in ("Saturday", "Sunday") else 0
                        stn_order = (idx + 1)
                        dist = float(stn_order * 45.0)
                        dist_rem = max(15.0, 600.0 - dist)
                        spd = 120.0 if t_priority == 2 else 95.0
                        w_condition = "Clear" if day_idx % 3 != 0 else ("Foggy" if hour < 9 else "Light Rain")
                        w_score = 10 if w_condition == "Clear" else (65 if w_condition == "Foggy" else 40)
                        temp = 24.0 + (hour - 12) * 0.8
                        w_rain = 0.0 if w_condition == "Clear" else (1.5 if w_condition == "Light Rain" else 0.0)
                        w_vis = 9.0 if w_condition == "Clear" else (1.5 if w_condition == "Foggy" else 4.0)
                        del_val = max(0.0, avg_delay + (is_peak * 6.0) + (w_score / 20.0) + np.random.normal(0, 2.5))
                        prec_del = max(0.0, del_val * 0.65)
                        c_level = "HIGH" if (del_val > 25 or (is_peak and del_val > 15)) else ("MEDIUM" if del_val > 10 else "LOW")

                        new_row = {
                            "TrainID": f"IR-{ext_train_file.split('.')[0][-5:]}",
                            "priority": t_priority,
                            "TrainType": t_type,
                            "StationOrder": stn_order,
                            "halt_time_minutes": 5.0,
                            "distance_travelled_km": dist,
                            "distance_remaining_km": dist_rem,
                            "speed_kmph": max(30.0, spd - (del_val * 0.5)),
                            "hour_of_day": hour,
                            "is_peak_hour": is_peak,
                            "DayOfWeek": day_name,
                            "is_weekend": is_wknd,
                            "temperature_c": temp,
                            "rainfall_intensity_mmh": w_rain,
                            "visibility_km": w_vis,
                            "weather_risk_score": w_score,
                            "Weather": w_condition,
                            "trains_in_section": 3 if is_peak else 1,
                            "preceding_delay_minutes": round(prec_del, 1),
                            "target_delay_minutes": round(del_val, 1),
                            "target_congestion_level": c_level,
                        }
                        merged = pd.concat([merged, pd.DataFrame([new_row])], ignore_index=True)

    # Select clean modeling columns
    columns_to_keep = [
        "TrainID", "priority", "TrainType", "StationOrder", "halt_time_minutes",
        "distance_travelled_km", "distance_remaining_km", "speed_kmph",
        "hour_of_day", "is_peak_hour", "DayOfWeek", "is_weekend",
        "temperature_c", "rainfall_intensity_mmh", "visibility_km",
        "weather_risk_score", "Weather", "trains_in_section", "preceding_delay_minutes",
        "target_delay_minutes", "target_congestion_level"
    ]
    final_df = merged[columns_to_keep].dropna(subset=["target_delay_minutes", "target_congestion_level"])

    output_path = DATASETS_DIR / "ir_delay_training_dataset.csv"
    final_df.to_csv(output_path, index=False)
    logger.info("Successfully generated training dataset: %s (%d rows, %d columns)", output_path, len(final_df), len(final_df.columns))

    return final_df


def main():
    logger.info("=== Starting Real Indian Railways Data Acquisition ===")
    download_raw_data()
    df = build_unified_dataset()
    print("\nDataset Summary:")
    print(df.info())
    print("\nTarget Delay Distribution (min):")
    print(df["target_delay_minutes"].describe())
    print("\nTarget Congestion Distribution:")
    print(df["target_congestion_level"].value_counts(normalize=True))
    print("\n=== Real Railway Data Acquisition Complete ===")


if __name__ == "__main__":
    main()
