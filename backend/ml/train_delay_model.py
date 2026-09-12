"""
RailTrack Machine Learning Model Training Pipeline
==================================================
Trains and validates production predictive models on real Indian Railways operational data:
1. Delay Minutes Regressor: Continuous delay prediction in minutes (Gradient Boosting vs Random Forest vs Ridge vs Naive Baseline)
2. Track Congestion Classifier: Section congestion tier classification (LOW / MEDIUM / HIGH)

Strictly adheres to ML best practices:
- Featurization ordering: Train/Test split BEFORE any encoder or scaler fitting
- Missing value analysis & contextual imputation
- Comprehensive metrics: MAE, RMSE, R^2, Macro F1, Precision, Recall, Confusion Matrix
- Model persistence via joblib into data/models/
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, RandomForestClassifier, GradientBoostingClassifier
from sklearn.dummy import DummyRegressor, DummyClassifier
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    f1_score,
    precision_score,
    recall_score,
    accuracy_score,
    confusion_matrix,
    classification_report
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE_DIR / "data" / "datasets" / "ir_delay_training_dataset.csv"
MODELS_DIR = BASE_DIR / "data" / "models"


def load_and_verify_data() -> pd.DataFrame:
    """Load dataset and perform schema/missing value checks."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Training dataset not found at {DATA_PATH}. Run fetch_real_data.py first.")

    df = pd.read_csv(DATA_PATH)
    logger.info("Loaded training data: %d rows, %d columns", len(df), len(df.columns))

    # Missing value audit
    missing = df.isnull().sum()
    missing_cols = missing[missing > 0]
    if not missing_cols.empty:
        logger.info("Missing values detected:\n%s", missing_cols)
    else:
        logger.info("Zero missing values in dataset.")

    return df


def create_preprocessor(numeric_features, categorical_features) -> ColumnTransformer:
    """Build preprocessing pipeline fitted strictly on training data."""
    num_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    cat_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipeline, numeric_features),
            ("cat", cat_pipeline, categorical_features),
        ]
    )
    return preprocessor


def train_delay_regressor(df: pd.DataFrame) -> Tuple[Pipeline, Dict[str, Any]]:
    """
    Train and compare multiple models to predict continuous delay in minutes.
    Models evaluated: Naive Baseline, Ridge Regression, Random Forest, Gradient Boosting.
    """
    logger.info("--- Starting Delay Regressor Model Comparison ---")

    features_num = [
        "priority", "StationOrder", "halt_time_minutes",
        "distance_travelled_km", "distance_remaining_km", "speed_kmph",
        "hour_of_day", "is_peak_hour", "is_weekend", "temperature_c",
        "rainfall_intensity_mmh", "visibility_km", "weather_risk_score",
        "trains_in_section", "preceding_delay_minutes"
    ]
    features_cat = ["TrainType", "DayOfWeek", "Weather"]

    X = df[features_num + features_cat]
    y = df["target_delay_minutes"]

    # Strict 80/20 train/test split BEFORE fitting preprocessor
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    logger.info("Train set: %d samples, Test set: %d samples", len(X_train), len(X_test))

    # Define candidate models
    candidates = {
        "Naive Median Baseline": DummyRegressor(strategy="median"),
        "Ridge Linear Regression": Ridge(alpha=1.0),
        "Random Forest Regressor": RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1),
        "Gradient Boosting Regressor": GradientBoostingRegressor(n_estimators=120, learning_rate=0.08, max_depth=5, random_state=42),
    }

    results = {}
    best_name = None
    best_pipe = None
    best_mae = float("inf")

    for name, model in candidates.items():
        preprocessor = create_preprocessor(features_num, features_cat)
        pipe = Pipeline([
            ("preprocessor", preprocessor),
            ("model", model),
        ])

        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        results[name] = {
            "MAE_minutes": round(float(mae), 3),
            "RMSE_minutes": round(float(rmse), 3),
            "R2_score": round(float(r2), 3),
        }
        logger.info("Candidate [%s] -> MAE: %.2f min | RMSE: %.2f min | R^2: %.3f", name, mae, rmse, r2)

        if mae < best_mae:
            best_mae = mae
            best_name = name
            best_pipe = pipe

    logger.info("Winner Regressor: %s (MAE=%.2f min)", best_name, best_mae)
    results["best_model"] = best_name
    return best_pipe, results


def train_congestion_classifier(df: pd.DataFrame) -> Tuple[Pipeline, Dict[str, Any]]:
    """
    Train and compare classifiers to predict track congestion level (LOW, MEDIUM, HIGH).
    """
    logger.info("--- Starting Congestion Classifier Training ---")

    features_num = [
        "priority", "StationOrder", "distance_travelled_km", "speed_kmph",
        "hour_of_day", "is_peak_hour", "weather_risk_score",
        "trains_in_section", "target_delay_minutes"
    ]
    features_cat = ["TrainType", "Weather"]

    X = df[features_num + features_cat]
    y = df["target_congestion_level"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    candidates = {
        "Majority Baseline": DummyClassifier(strategy="most_frequent"),
        "Random Forest Classifier": RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
        "Gradient Boosting Classifier": GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42),
    }

    results = {}
    best_name = None
    best_pipe = None
    best_f1 = -1.0

    for name, model in candidates.items():
        preprocessor = create_preprocessor(features_num, features_cat)
        pipe = Pipeline([
            ("preprocessor", preprocessor),
            ("model", model),
        ])

        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
        prec = precision_score(y_test, y_pred, average="macro", zero_division=0)
        rec = recall_score(y_test, y_pred, average="macro", zero_division=0)

        results[name] = {
            "Accuracy": round(float(acc), 3),
            "Macro_F1": round(float(f1), 3),
            "Precision": round(float(prec), 3),
            "Recall": round(float(rec), 3),
        }
        logger.info("Candidate [%s] -> Accuracy: %.3f | Macro F1: %.3f", name, acc, f1)

        if f1 > best_f1:
            best_f1 = f1
            best_name = name
            best_pipe = pipe

    # Confusion matrix for winner
    y_pred_best = best_pipe.predict(X_test)
    cm = confusion_matrix(y_test, y_pred_best, labels=["LOW", "MEDIUM", "HIGH"])
    results["confusion_matrix"] = {
        "labels": ["LOW", "MEDIUM", "HIGH"],
        "matrix": cm.tolist()
    }
    results["best_model"] = best_name
    logger.info("Winner Classifier: %s (Macro F1=%.3f)", best_name, best_f1)

    return best_pipe, results


def save_models(
    delay_pipe: Pipeline,
    congestion_pipe: Pipeline,
    delay_metrics: Dict[str, Any],
    congestion_metrics: Dict[str, Any]
) -> None:
    """Serialize trained pipelines and export model metadata."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    delay_path = MODELS_DIR / "delay_regressor.joblib"
    congestion_path = MODELS_DIR / "congestion_classifier.joblib"
    meta_path = MODELS_DIR / "model_metadata.json"

    logger.info("Saving models to %s...", MODELS_DIR)
    joblib.dump(delay_pipe, delay_path)
    joblib.dump(congestion_pipe, congestion_path)

    metadata = {
        "version": "IR-GBM-DelayPredictor-v2.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_dataset": str(DATA_PATH.name),
        "delay_regression": delay_metrics,
        "congestion_classification": congestion_metrics,
        "frameworks": {
            "scikit-learn": joblib.__version__,
            "joblib": joblib.__version__,
        }
    }
    meta_path.write_text(json.dumps(metadata, indent=2))
    logger.info("Model artifacts & metadata saved successfully.")


def main():
    logger.info("=== Starting RailTrack ML Model Training ===")
    df = load_and_verify_data()

    delay_pipe, delay_metrics = train_delay_regressor(df)
    congestion_pipe, congestion_metrics = train_congestion_classifier(df)

    save_models(delay_pipe, congestion_pipe, delay_metrics, congestion_metrics)

    print("\n" + "=" * 60)
    print("TRAINING RUN COMPLETE")
    print("=" * 60)
    print("Delay Regression Results:")
    for k, v in delay_metrics.items():
        print(f"  {k}: {v}")
    print("\nCongestion Classification Results:")
    for k, v in congestion_metrics.items():
        print(f"  {k}: {v}")
    print("=" * 60)


if __name__ == "__main__":
    main()
