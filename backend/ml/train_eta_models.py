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

from backend.ml.feature_engineering import FEATURES_NUM, FEATURES_CAT

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
    Returns dictionary of trained pipelines and complete comparative evaluation report.
    """
    df = load_and_prepare_dataset()
    X = df[FEATURES_NUM + FEATURES_CAT]
    y = df["target_remaining_travel_time_minutes"]

    # 1. 80/20 Train/Test split BEFORE any fitting
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    logger.info("Dataset split: Train=%d, Test=%d", len(X_train_full), len(X_test))

    # 2. Further split train into train (80%) and validation (20%) for ensemble weight optimization
    X_train_sub, X_val, y_train_sub, y_val = train_test_split(
        X_train_full, y_train_full, test_size=0.20, random_state=42
    )

    # Dictionary of builders
    builders = {
        "XGBoost": train_xgboost,
        "Random Forest": train_random_forest,
        "SVR": train_svr,
        "Gradient Boosting": train_gradient_boosting,
        "Decision Tree": train_decision_tree,
    }

    # 3. Fit on train_sub to obtain out-of-sample validation predictions for ensemble weight tuning
    val_preds = {}
    for name, builder in builders.items():
        sub_pipe = builder(X_train_sub, y_train_sub, create_base_preprocessor())
        val_preds[name] = sub_pipe.predict(X_val)

    ensemble_weights = optimize_ensemble_weights(val_preds, y_val.values)
    logger.info("Optimized ensemble weights: %s", ensemble_weights)

    # 4. Now train each model on the full X_train_full for official evaluation on X_test
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

        # Evaluation on test partition
        y_pred = pipe.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        metrics_report[name] = {
            "MAE": round(float(mae), 3),
            "RMSE": round(float(rmse), 3),
            "R2": round(float(r2), 4),
            "CV_5Fold_MAE": cv_mae,
            "CV_5Fold_Std": cv_std,
        }
        fitted_pipelines[name] = pipe
        logger.info("[%s] -> Test MAE: %.3f min | RMSE: %.3f min | R^2: %.4f | 5-Fold CV: %.3f±%.3f", name, mae, rmse, r2, cv_mae, cv_std)

    # 5. Evaluate Ensemble on X_test
    test_preds_matrix = np.column_stack([fitted_pipelines[m].predict(X_test) for m in builders.keys()])
    weights_vector = np.array([ensemble_weights[m] for m in builders.keys()])
    y_pred_ensemble = test_preds_matrix @ weights_vector

    ens_mae = mean_absolute_error(y_test, y_pred_ensemble)
    ens_rmse = np.sqrt(mean_squared_error(y_test, y_pred_ensemble))
    ens_r2 = r2_score(y_test, y_pred_ensemble)

    metrics_report["Ensemble"] = {
        "MAE": round(float(ens_mae), 3),
        "RMSE": round(float(ens_rmse), 3),
        "R2": round(float(ens_r2), 4),
        "weights": ensemble_weights,
    }
    logger.info("[Ensemble] -> Test MAE: %.3f min | RMSE: %.3f min | R^2: %.4f", ens_mae, ens_rmse, ens_r2)

    # 6. Objective Model Selection
    # Identify the best individual model based on lowest Test MAE
    individual_models = [m for m in builders.keys()]
    best_single_name = min(individual_models, key=lambda m: metrics_report[m]["MAE"])
    best_single_mae = metrics_report[best_single_name]["MAE"]

    # Compare Ensemble with best single model
    ensemble_improved = ens_mae < best_single_mae
    selected_champion = "Ensemble" if ensemble_improved else best_single_name

    logger.info("Best Single Model: %s (MAE=%.3f)", best_single_name, best_single_mae)
    logger.info("Ensemble Performance: MAE=%.3f (Improved: %s)", ens_mae, ensemble_improved)
    logger.info("Designated Production Champion: %s", selected_champion)

    comparison_summary = {
        "models": metrics_report,
        "best_individual_model": best_single_name,
        "ensemble_weights": ensemble_weights,
        "ensemble_improved": ensemble_improved,
        "selected_production_model": selected_champion,
        "target_variable": "target_remaining_travel_time_minutes",
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "train_samples": len(X_train_full),
        "test_samples": len(X_test),
        "data_honesty_statement": "Model performance depends on the quality and representativeness of the training data.",
    }

    return fitted_pipelines, comparison_summary


def save_all_models(fitted_pipelines: Dict[str, Pipeline], comparison_summary: Dict[str, Any]) -> None:
    """Save all 5 trained models, preprocessor, and comparison metrics to data/models/."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # File mapping
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

    # Save champion model to eta_model.joblib for backward compatibility
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
