"""
RailTrack Machine Learning Model Training Pipeline
==================================================
Trains and validates production predictive models on real Indian Railways operational data:
1. Dynamic Delay / Travel Time Regressor: Continuous delay and remaining travel time prediction via XGBoost
   (with rigorous benchmark comparison against Random Forest, Gradient Boosting, and Ridge baselines)
2. Track Congestion Classifier: Section congestion tier classification (LOW / MEDIUM / HIGH)

Strictly adheres to ML best practices:
- Featurization ordering: Train/Test split BEFORE any encoder or scaler fitting
- Missing value analysis & contextual imputation
- Comprehensive metrics: MAE, RMSE, R^2, Macro F1, Precision, Recall, Confusion Matrix
- Model persistence via joblib into data/models/ as delay_regressor.joblib and eta_model.joblib
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
import joblib
import xgboost
from xgboost import XGBRegressor

from sklearn.model_selection import train_test_split, KFold, StratifiedKFold, cross_val_score
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

from backend.ml.feature_engineering import FEATURES_NUM, FEATURES_CAT

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
        logger.info("Missing values detected: %s", missing_cols.to_dict())
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
    Train and rigorously compare multiple regression models with 5-fold cross-validation.
    Models evaluated: Naive Baseline, Ridge Regression, Random Forest Baseline, Gradient Boosting, and XGBoost Regressor.
    Returns the designated production XGBoost pipeline and the complete comparative metrics dictionary.
    """
    logger.info("--- Starting Delay / ETA Regressor Model Comparison with 5-Fold Cross-Validation ---")

    X = df[FEATURES_NUM + FEATURES_CAT]
    y = df["target_delay_minutes"]

    # Strict 80/20 train/test split BEFORE fitting preprocessor
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    logger.info("Train set: %d samples, Test set: %d samples", len(X_train), len(X_test))

    # Define candidate models including XGBoost and the Random Forest baseline
    candidates = {
        "Naive Median Baseline": DummyRegressor(strategy="median"),
        "Ridge Linear Regression": Ridge(alpha=1.0),
        "Random Forest Baseline": RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1),
        "Gradient Boosting Regressor": GradientBoostingRegressor(n_estimators=120, learning_rate=0.08, max_depth=5, random_state=42),
        "XGBoost Regressor": XGBRegressor(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
        ),
    }

    results = {}
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    fitted_pipelines = {}

    for name, model in candidates.items():
        preprocessor = create_preprocessor(FEATURES_NUM, FEATURES_CAT)
        pipe = Pipeline([
            ("preprocessor", preprocessor),
            ("model", model),
        ])

        # 5-fold cross validation on training partition
        cv_scores = cross_val_score(pipe, X_train, y_train, cv=kf, scoring="neg_mean_absolute_error", n_jobs=-1)
        cv_mae = round(float(-cv_scores.mean()), 3)
        cv_std = round(float(cv_scores.std()), 3)

        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        results[name] = {
            "MAE_minutes": round(float(mae), 3),
            "RMSE_minutes": round(float(rmse), 3),
            "R2_score": round(float(r2), 3),
            "CV_5Fold_MAE": cv_mae,
            "CV_5Fold_Std": cv_std,
        }
        fitted_pipelines[name] = pipe
        logger.info("Candidate [%s] -> Test MAE: %.2f min | 5-Fold CV MAE: %.2f±%.2f | R^2: %.3f", name, mae, cv_mae, cv_std, r2)

    # Primary production model is XGBoost Regressor
    xgb_pipe = fitted_pipelines["XGBoost Regressor"]
    xgb_mae = results["XGBoost Regressor"]["MAE_minutes"]
    rf_mae = results["Random Forest Baseline"]["MAE_minutes"]

    logger.info("XGBoost Regressor Test MAE: %.3f min vs Random Forest Baseline: %.3f min", xgb_mae, rf_mae)
    results["primary_model"] = "XGBoost Regressor"
    results["rf_vs_xgb_comparison"] = {
        "rf_test_mae": rf_mae,
        "xgb_test_mae": xgb_mae,
        "improvement_pct": round(((rf_mae - xgb_mae) / max(0.001, rf_mae)) * 100.0, 2) if rf_mae > 0 else 0.0,
    }

    return xgb_pipe, results


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
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for name, model in candidates.items():
        preprocessor = create_preprocessor(features_num, features_cat)
        pipe = Pipeline([
            ("preprocessor", preprocessor),
            ("model", model),
        ])

        cv_f1_scores = cross_val_score(pipe, X_train, y_train, cv=skf, scoring="f1_macro", n_jobs=-1)
        cv_f1 = round(float(cv_f1_scores.mean()), 3)
        cv_f1_std = round(float(cv_f1_scores.std()), 3)

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
            "CV_5Fold_Macro_F1": cv_f1,
            "CV_5Fold_Std": cv_f1_std,
        }
        logger.info("Candidate [%s] -> Test Acc: %.3f | Test F1: %.3f | 5-Fold CV F1: %.3f±%.3f", name, acc, f1, cv_f1, cv_f1_std)

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
    """Serialize trained XGBoost pipeline and export model metadata."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    delay_path = MODELS_DIR / "delay_regressor.joblib"
    eta_path = MODELS_DIR / "eta_model.joblib"
    congestion_path = MODELS_DIR / "congestion_classifier.joblib"
    meta_path = MODELS_DIR / "model_metadata.json"

    logger.info("Saving models to %s...", MODELS_DIR)
    joblib.dump(delay_pipe, delay_path)
    joblib.dump(delay_pipe, eta_path)
    joblib.dump(congestion_pipe, congestion_path)

    metadata = {
        "version": "IR-XGB-DelayPredictor-v3.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_dataset": str(DATA_PATH.name),
        "primary_eta_model": "XGBoost Regressor",
        "delay_regression": delay_metrics,
        "congestion_classification": congestion_metrics,
        "frameworks": {
            "xgboost": getattr(xgboost, "__version__", "3.4.1"),
            "scikit-learn": joblib.__version__,
            "joblib": joblib.__version__,
        }
    }
    meta_path.write_text(json.dumps(metadata, indent=2))
    logger.info("Model artifacts (delay_regressor.joblib, eta_model.joblib) & metadata saved successfully.")


def main():
    logger.info("=== Starting RailTrack XGBoost ML Model Training ===")
    df = load_and_verify_data()

    delay_pipe, delay_metrics = train_delay_regressor(df)
    congestion_pipe, congestion_metrics = train_congestion_classifier(df)

    save_models(delay_pipe, congestion_pipe, delay_metrics, congestion_metrics)

    print("=" * 60)
    print("TRAINING RUN COMPLETE (XGBoost v3.0)")
    print("=" * 60)
    print("Delay / ETA Regression Results:")
    for k, v in delay_metrics.items():
        print(f"  {k}: {v}")
    print("Congestion Classification Results:")
    for k, v in congestion_metrics.items():
        print(f"  {k}: {v}")
    print("=" * 60)


if __name__ == "__main__":
    main()
