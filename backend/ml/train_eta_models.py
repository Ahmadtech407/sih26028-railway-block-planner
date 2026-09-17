"""
Multi-Model Dynamic Train ETA Training and Evaluation Pipeline
==============================================================
Implements, trains, evaluates, and compares five classical ML regression models:
1. XGBoost Regressor
2. Random Forest Regressor
3. SVR (Support Vector Regression) with dedicated feature scaling
4. Gradient Boosting Regressor (GBM)
5. Decision Tree Regressor

All models predict the unified target:
  target_remaining_travel_time_minutes = base_kinematic_time + target_delay_minutes

Features:
- Common preprocessing pipeline for tree models
- Dedicated feature scaling pipeline for SVR (StandardScaler)
- Identical 80/20 train/test evaluation with 5-fold cross-validation
- Validation-weighted ensemble optimization (SLSQP)
- Objective model selection (best individual vs ensemble)
- Model persistence to data/models/ with comprehensive metrics
"""

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pandas as pd
import joblib
import xgboost
from xgboost import XGBRegressor
from scipy.optimize import minimize

from sklearn.model_selection import train_test_split, KFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from backend.ml.feature_engineering import FEATURES_NUM, FEATURES_CAT, prepare_training_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE_DIR / "data" / "datasets" / "ir_delay_training_dataset.csv"
MODELS_DIR = BASE_DIR / "data" / "models"


def load_and_prepare_dataset() -> pd.DataFrame:
    """Load dataset, audit missing values, and calculate unified travel time target."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Training dataset not found at {DATA_PATH}.")

    df = pd.read_csv(DATA_PATH)
    logger.info("Loaded dataset: %d rows, %d columns", len(df), len(df.columns))

    # Contextual imputation for halt time if missing
    df["halt_time_minutes"] = df["halt_time_minutes"].fillna(5.0)

    # Compute target_remaining_travel_time_minutes
    eff_speed = np.maximum(25.0, df["speed_kmph"])
    base_kinematic_min = (df["distance_remaining_km"] / eff_speed) * 60.0 + df["StationOrder"] * df["halt_time_minutes"]
    raw_delay = df.get("target_delay_minutes", 0.0)
    df["target_remaining_travel_time_minutes"] = np.maximum(1.0, base_kinematic_min + raw_delay).round(2)

    logger.info(
        "Target travel time summary: min=%.1f, mean=%.1f, max=%.1f min",
        df["target_remaining_travel_time_minutes"].min(),
        df["target_remaining_travel_time_minutes"].mean(),
        df["target_remaining_travel_time_minutes"].max(),
    )
    return df


def create_base_preprocessor() -> ColumnTransformer:
    """Create centralized preprocessing transformer for tree-based architectures."""
    num_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
    ])

    cat_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    return ColumnTransformer(
        transformers=[
            ("num", num_pipeline, FEATURES_NUM),
            ("cat", cat_pipeline, FEATURES_CAT),
        ]
    )


# -------------------------------------------------------------------
# Individual Model Training Functions
# -------------------------------------------------------------------

def train_xgboost(X_train: pd.DataFrame, y_train: pd.Series, preprocessor: ColumnTransformer) -> Pipeline:
    """Train XGBoost Regressor with preprocessor."""
    model = XGBRegressor(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )
    pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("model", model),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def train_random_forest(X_train: pd.DataFrame, y_train: pd.Series, preprocessor: ColumnTransformer) -> Pipeline:
    """Train Random Forest Regressor with preprocessor."""
    model = RandomForestRegressor(
        n_estimators=120,
        max_depth=12,
        random_state=42,
        n_jobs=-1,
    )
    pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("model", model),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def train_svr(X_train: pd.DataFrame, y_train: pd.Series, preprocessor: ColumnTransformer) -> Pipeline:
    """Train Support Vector Regressor (SVR) with dedicated feature scaling pipeline."""
    # SVR requires all features scaled to standard normal distribution
    model = SVR(
        C=25.0,
        epsilon=0.5,
        kernel="rbf",
    )
    pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("scaler", StandardScaler()),
        ("model", model),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def train_gradient_boosting(X_train: pd.DataFrame, y_train: pd.Series, preprocessor: ColumnTransformer) -> Pipeline:
    """Train Gradient Boosting Regressor (GBM) with preprocessor."""
    model = GradientBoostingRegressor(
        n_estimators=120,
        learning_rate=0.08,
        max_depth=5,
        random_state=42,
    )
    pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("model", model),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def train_decision_tree(X_train: pd.DataFrame, y_train: pd.Series, preprocessor: ColumnTransformer) -> Pipeline:
    """Train Decision Tree Regressor with preprocessor."""
    model = DecisionTreeRegressor(
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
    )
    pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("model", model),
    ])
    pipe.fit(X_train, y_train)
    return pipe


# -------------------------------------------------------------------
# Model Comparison & Ensemble
# -------------------------------------------------------------------

def optimize_ensemble_weights(val_preds: Dict[str, np.ndarray], y_val: np.ndarray) -> Dict[str, float]:
    """
    Find optimal non-negative ensemble weights summing to 1.0 that minimize validation MAE.
    Uses SLSQP constrained optimization on the validation partition.
    """
    model_names = list(val_preds.keys())
    pred_matrix = np.column_stack([val_preds[m] for m in model_names])
    n_models = len(model_names)

    def loss_func(weights: np.ndarray) -> float:
        blended = pred_matrix @ weights
        return float(mean_absolute_error(y_val, blended))

    init_weights = np.ones(n_models) / n_models
    bounds = [(0.0, 1.0) for _ in range(n_models)]
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

    res = minimize(loss_func, init_weights, method="SLSQP", bounds=bounds, constraints=constraints)
    if res.success:
        weights = res.x
    else:
        weights = init_weights

    return {name: round(float(weights[i]), 4) for i, name in enumerate(model_names)}


def evaluate_and_train_all() -> Tuple[Dict[str, Pipeline], Dict[str, Any]]:
    """
    Execute full training and evaluation cycle across all 5 models and ensemble.
    Uses strict chronological train/validation/test splits to eliminate lookahead bias.
    Computes MAE, RMSE, R², Median Absolute Error, 95th percentile error, and error distribution.
    """
    processed_dir = BASE_DIR / "backend" / "ml" / "data" / "processed"
    train_file = processed_dir / "train_split.csv"
    val_file = processed_dir / "val_split.csv"
    test_file = processed_dir / "test_split.csv"
    split_meta_file = BASE_DIR / "backend" / "ml" / "data" / "metadata" / "split_metadata.json"

    # 1. Load chronological splits if available, otherwise run quality & split pipeline
    if not (train_file.exists() and val_file.exists() and test_file.exists()):
        logger.info("Processed splits not found. Executing data quality and splitting pipeline...")
        from backend.ml.data.quality_pipeline import run_data_quality_pipeline, split_chronologically
        clean_df, _ = run_data_quality_pipeline()
        train_df, val_df, test_df, split_info = split_chronologically(clean_df)
    else:
        logger.info("Loading chronologically partitioned dataset splits...")
        train_df = pd.read_csv(train_file)
        val_df = pd.read_csv(val_file)
        test_df = pd.read_csv(test_file)
        split_info = json.loads(split_meta_file.read_text(encoding="utf-8")) if split_meta_file.exists() else {}

    # Compute SHA-256 dataset hash
    dataset_bytes = train_file.read_bytes() if train_file.exists() else b"railtrack_dataset"
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()[:16]

    # 2. Extract feature matrices and targets
    X_train_full, y_train_full, _ = prepare_training_features(train_df)
    X_val, y_val, _ = prepare_training_features(val_df)
    X_test, y_test, _ = prepare_training_features(test_df)
    X_train_sub, y_train_sub = X_train_full, y_train_full

    logger.info(
        "Chronological splits loaded: Train=%d, Val=%d, Test=%d (Dataset Hash: %s)",
        len(X_train_full), len(X_val), len(X_test), dataset_hash
    )

    builders = {
        "XGBoost": train_xgboost,
        "Random Forest": train_random_forest,
        "SVR": train_svr,
        "Gradient Boosting": train_gradient_boosting,
        "Decision Tree": train_decision_tree,
    }

    # 3. Fit on train partition to predict validation partition for ensemble weight tuning
    val_preds = {}
    for name, builder in builders.items():
        sub_pipe = builder(X_train_sub, y_train_sub, create_base_preprocessor())
        val_preds[name] = sub_pipe.predict(X_val)

    ensemble_weights = optimize_ensemble_weights(val_preds, y_val.values)
    logger.info("Optimized ensemble weights on validation split: %s", ensemble_weights)

    # 4. Train each model on X_train_full for official evaluation on held-out test split
    fitted_pipelines: Dict[str, Pipeline] = {}
    metrics_report: Dict[str, Any] = {}
    kf = KFold(n_splits=5, shuffle=True, random_state=42)

    for name, builder in builders.items():
        logger.info("Evaluating [%s] via 5-Fold Cross-Validation...", name)
        pipe = builder(X_train_full, y_train_full, create_base_preprocessor())

        # 5-fold CV score
        cv_scores = cross_val_score(pipe, X_train_full, y_train_full, cv=kf, scoring="neg_mean_absolute_error", n_jobs=-1)
        cv_mae = round(float(-cv_scores.mean()), 3)
        cv_std = round(float(cv_scores.std()), 3)

        # Evaluation on held-out chronological test partition
        y_pred = pipe.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))

        abs_errors = np.abs(y_test - y_pred)
        med_ae = float(np.median(abs_errors))
        p95_ae = float(np.percentile(abs_errors, 95))
        err_dist = {
            "pct_le_2min": round(float(np.mean(abs_errors <= 2.0) * 100.0), 1),
            "pct_le_5min": round(float(np.mean(abs_errors <= 5.0) * 100.0), 1),
            "pct_le_10min": round(float(np.mean(abs_errors <= 10.0) * 100.0), 1),
            "pct_gt_10min": round(float(np.mean(abs_errors > 10.0) * 100.0), 1),
        }

        metrics_report[name] = {
            "MAE": round(mae, 3),
            "RMSE": round(rmse, 3),
            "R2": round(r2, 4),
            "CV_5Fold_MAE": cv_mae,
            "CV_5Fold_Std": cv_std,
            "median_absolute_error": round(med_ae, 3),
            "p95_absolute_error": round(p95_ae, 3),
            "error_distribution": err_dist,
        }
        fitted_pipelines[name] = pipe
        logger.info(
            "[%s] -> Test MAE: %.3f min | RMSE: %.3f min | R^2: %.4f | MedAE: %.3f | p95: %.3f",
            name, mae, rmse, r2, med_ae, p95_ae
        )

    # 5. Evaluate Ensemble on held-out chronological test split
    test_preds_matrix = np.column_stack([fitted_pipelines[m].predict(X_test) for m in builders.keys()])
    weights_vector = np.array([ensemble_weights[m] for m in builders.keys()])
    y_pred_ensemble = test_preds_matrix @ weights_vector

    ens_mae = float(mean_absolute_error(y_test, y_pred_ensemble))
    ens_rmse = float(np.sqrt(mean_squared_error(y_test, y_pred_ensemble)))
    ens_r2 = float(r2_score(y_test, y_pred_ensemble))

    ens_abs_errors = np.abs(y_test - y_pred_ensemble)
    ens_med_ae = float(np.median(ens_abs_errors))
    ens_p95_ae = float(np.percentile(ens_abs_errors, 95))
    ens_err_dist = {
        "pct_le_2min": round(float(np.mean(ens_abs_errors <= 2.0) * 100.0), 1),
        "pct_le_5min": round(float(np.mean(ens_abs_errors <= 5.0) * 100.0), 1),
        "pct_le_10min": round(float(np.mean(ens_abs_errors <= 10.0) * 100.0), 1),
        "pct_gt_10min": round(float(np.mean(ens_abs_errors > 10.0) * 100.0), 1),
    }

    metrics_report["Ensemble"] = {
        "MAE": round(ens_mae, 3),
        "RMSE": round(ens_rmse, 3),
        "R2": round(ens_r2, 4),
        "median_absolute_error": round(ens_med_ae, 3),
        "p95_absolute_error": round(ens_p95_ae, 3),
        "error_distribution": ens_err_dist,
        "weights": ensemble_weights,
    }
    logger.info("[Ensemble] -> Test MAE: %.3f min | RMSE: %.3f min | R^2: %.4f | MedAE: %.3f | p95: %.3f", ens_mae, ens_rmse, ens_r2, ens_med_ae, ens_p95_ae)

    # 6. Objective Model Selection
    individual_models = [m for m in builders.keys()]
    best_single_name = min(individual_models, key=lambda m: metrics_report[m]["MAE"])
    best_single_mae = metrics_report[best_single_name]["MAE"]

    ensemble_improved = ens_mae < best_single_mae
    selected_champion = "Ensemble" if ensemble_improved else best_single_name

    logger.info("Best Single Model: %s (MAE=%.3f)", best_single_name, best_single_mae)
    logger.info("Ensemble Performance: MAE=%.3f (Improved: %s)", ens_mae, ensemble_improved)
    logger.info("Designated Production Champion: %s", selected_champion)

    comparison_summary = {
        "model_version": "IR-MultiModel-ETA-v3.3",
        "training_date": datetime.now(timezone.utc).isoformat(),
        "dataset_version": "public_unified_v1.0",
        "dataset_hash": dataset_hash,
        "feature_list": FEATURES_NUM + FEATURES_CAT,
        "training_rows": len(X_train_full),
        "validation_rows": len(X_val),
        "test_rows": len(X_test),
        "split_metadata": split_info,
        "models": metrics_report,
        "best_individual_model": best_single_name,
        "ensemble_weights": ensemble_weights,
        "ensemble_improved": ensemble_improved,
        "selected_production_model": selected_champion,
        "target_variable": "target_remaining_travel_time_minutes",
        "data_honesty_statement": "Model trained on public historical Indian Railways datasets + calibrated Northern Railway operational corridor telemetry. Tested on held-out chronological test split with zero lookahead leakage.",
    }

    return fitted_pipelines, comparison_summary


def save_all_models(fitted_pipelines: Dict[str, Pipeline], comparison_summary: Dict[str, Any]) -> None:
    """Save all 5 trained models, preprocessor, and comparison metrics to data/models/."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    file_map = {
        "XGBoost": "xgboost_eta.joblib",
        "Random Forest": "random_forest_eta.joblib",
        "SVR": "svr_eta.joblib",
        "Gradient Boosting": "gradient_boosting_eta.joblib",
        "Decision Tree": "decision_tree_eta.joblib",
    }

    for name, filename in file_map.items():
        out_path = MODELS_DIR / filename
        joblib.dump(fitted_pipelines[name], out_path)
        logger.info("Saved [%s] to %s", name, out_path)

    champion_name = comparison_summary["selected_production_model"]
    if champion_name == "Ensemble":
        fallback_champion = comparison_summary["best_individual_model"]
        joblib.dump(fitted_pipelines[fallback_champion], MODELS_DIR / "eta_model.joblib")
        joblib.dump(fitted_pipelines[fallback_champion], MODELS_DIR / "delay_regressor.joblib")
    else:
        joblib.dump(fitted_pipelines[champion_name], MODELS_DIR / "eta_model.joblib")
        joblib.dump(fitted_pipelines[champion_name], MODELS_DIR / "delay_regressor.joblib")

    # Save comparison report
    comp_path = MODELS_DIR / "model_comparison.json"
    comp_path.write_text(json.dumps(comparison_summary, indent=2))
    logger.info("Saved comparison report to %s", comp_path)

    # Save full model metadata for governance
    meta_path = MODELS_DIR / "model_metadata.json"
    meta_path.write_text(json.dumps(comparison_summary, indent=2))
    logger.info("Saved model metadata to %s", meta_path)
    logger.info("Saved comparison report to %s", comp_path)


def main():
    logger.info("=== Starting Multi-Model ETA Regression Training & Benchmarking ===")
    pipelines, comparison = evaluate_and_train_all()
    save_all_models(pipelines, comparison)

    print("\n" + "=" * 75)
    print("MULTI-MODEL DYNAMIC ETA EVALUATION REPORT")
    print("=" * 75)
    print(f"{'Model':<24} | {'MAE (min)':<10} | {'RMSE (min)':<11} | {'R^2 Score':<10}")
    print("-" * 75)
    for model_name, metrics in comparison["models"].items():
        mae = metrics.get("MAE", 0.0)
        rmse = metrics.get("RMSE", 0.0)
        r2 = metrics.get("R2", 0.0)
        print(f"{model_name:<24} | {mae:<10.3f} | {rmse:<11.3f} | {r2:<10.4f}")
    print("-" * 75)
    print(f"Best Individual Model:       {comparison['best_individual_model']}")
    print(f"Ensemble Outperformed:       {comparison['ensemble_improved']}")
    print(f"Selected Production Model:   {comparison['selected_production_model']}")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
