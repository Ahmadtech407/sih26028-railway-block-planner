"""
Model Registry for Multi-Model Dynamic Train ETA
=================================================
Manages offline trained classical regression models:
1. XGBoost Regressor
2. Random Forest Regressor
3. SVR (Support Vector Regression)
4. Gradient Boosting Regressor (GBM)
5. Decision Tree Regressor
Plus validation-weighted Ensemble.

Provides dynamic selection:
- "best_model": Automatically selects the empirically best model or ensemble
- "ensemble": Computes validation-weighted prediction across all models
- Specific model: "xgboost", "random_forest", "svr", "gradient_boosting", "decision_tree"
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = BASE_DIR / "data" / "models"


class ModelRegistry:
    """Registry maintaining references to all trained ETA regression models."""

    MODEL_FILES = {
        "xgboost": "xgboost_eta.joblib",
        "random_forest": "random_forest_eta.joblib",
        "svr": "svr_eta.joblib",
        "gradient_boosting": "gradient_boosting_eta.joblib",
        "decision_tree": "decision_tree_eta.joblib",
    }

    FORMAL_NAMES = {
        "xgboost": "XGBoost",
        "random_forest": "Random Forest",
        "svr": "SVR",
        "gradient_boosting": "Gradient Boosting",
        "decision_tree": "Decision Tree",
    }

    def __init__(self):
        self._models: Dict[str, Pipeline] = {}
        self._comparison: Dict[str, Any] = {}
        self._loaded: bool = False
        self._load_registry()

    def _load_registry(self) -> None:
        """Load all model artifacts and comparison summary from disk."""
        comp_file = MODELS_DIR / "model_comparison.json"
        if comp_file.exists():
            try:
                self._comparison = json.loads(comp_file.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Failed to parse model_comparison.json: %s", exc)

        for key, filename in self.MODEL_FILES.items():
            path = MODELS_DIR / filename
            if path.exists():
                try:
                    self._models[key] = joblib.load(path)
                except Exception as exc:
                    logger.warning("Could not load model %s: %s", key, exc)

        self._loaded = len(self._models) > 0

    def reload(self) -> None:
        """Reload all models and comparison summary from disk."""
        self._models.clear()
        self._comparison.clear()
        self._load_registry()
        logger.info("ModelRegistry reloaded. Active models: %s", list(self._models.keys()))

    def rollback_to_previous_champion(self) -> Dict[str, Any]:
        """Roll back production champion to previously saved champion state."""
        prev = self._comparison.get("previous_champion")
        if not prev:
            return {"status": "FAILED", "reason": "No previous champion recorded for rollback"}

        self._comparison["selected_production_model"] = prev.get("model_name", "Gradient Boosting")
        self._comparison["ensemble_weights"] = prev.get("weights", self.get_ensemble_weights())
        self._comparison["rollback_timestamp"] = datetime.now(timezone.utc).isoformat()

        comp_file = MODELS_DIR / "model_comparison.json"
        comp_file.write_text(json.dumps(self._comparison, indent=2), encoding="utf-8")
        self.reload()

        return {
            "status": "ROLLED_BACK",
            "active_champion": self._comparison["selected_production_model"],
            "timestamp": self._comparison["rollback_timestamp"],
        }

    def get_comparison(self) -> Dict[str, Any]:
        """Return raw model evaluation comparison dictionary."""
        return self._comparison

    def get_best_individual_model_key(self) -> str:
        """Return the key of the best single model based on validation MAE."""
        best_formal = self._comparison.get("best_individual_model", "Gradient Boosting")
        for k, v in self.FORMAL_NAMES.items():
            if v == best_formal:
                return k
        return "gradient_boosting"

    def get_champion_model_key(self) -> str:
        """Return production champion key (either 'ensemble' or single model key)."""
        champion_formal = self._comparison.get("selected_production_model", "Ensemble")
        if champion_formal == "Ensemble":
            return "ensemble"
        for k, v in self.FORMAL_NAMES.items():
            if v == champion_formal:
                return k
        return self.get_best_individual_model_key()

    def get_ensemble_weights(self) -> Dict[str, float]:
        """Return validation weights dictionary keyed by model key."""
        raw_weights = self._comparison.get("ensemble_weights", {})
        key_weights = {}
        for k, formal in self.FORMAL_NAMES.items():
            key_weights[k] = float(raw_weights.get(formal, 0.2))
        return key_weights

    def predict(
        self,
        features_df: pd.DataFrame,
        model_name: Optional[str] = "best_model"
    ) -> Tuple[float, str, Dict[str, float]]:
        """
        Execute inference using the requested model architecture.

        Parameters:
        - features_df: DataFrame containing the standardized feature vector
        - model_name: 'best_model', 'ensemble', 'xgboost', 'random_forest',
                      'svr', 'gradient_boosting', 'decision_tree'

        Returns:
        - (predicted_minutes, model_used_str, model_predictions_breakdown)
        """
        if not self._loaded:
            self._load_registry()

        normalized_key = str(model_name or "best_model").lower().replace(" ", "_").replace("-", "_")

        # Resolve champion / best aliases
        if normalized_key in ("best_model", "best", "default", "champion"):
            target_key = self.get_champion_model_key()
        elif normalized_key in ("ensemble", "weighted_ensemble"):
            target_key = "ensemble"
        elif normalized_key in ("gbm", "gradient_boosting_regressor"):
            target_key = "gradient_boosting"
        elif normalized_key in ("rf", "random_forest_regressor"):
            target_key = "random_forest"
        elif normalized_key in ("xgb", "xgboost_regressor"):
            target_key = "xgboost"
        elif normalized_key in ("tree", "decision_tree_regressor"):
            target_key = "decision_tree"
        elif normalized_key in self.MODEL_FILES:
            target_key = normalized_key
        else:
            target_key = self.get_champion_model_key()

        # Compute predictions for all available models (for breakdown and ensemble)
        predictions = {}
        for k, model in self._models.items():
            try:
                val = float(model.predict(features_df)[0])
                predictions[k] = max(0.0, val)
            except Exception as exc:
                logger.debug("Inference failed for %s: %s", k, exc)

        if not predictions:
            raise RuntimeError("No trained models could produce a valid prediction.")

        breakdown = {self.FORMAL_NAMES.get(k, k): round(v, 2) for k, v in predictions.items()}

        # 1. Ensemble prediction
        if target_key == "ensemble":
            weights = self.get_ensemble_weights()
            # Normalize weights over available models in predictions
            active_weights = {k: weights.get(k, 0.0) for k in predictions.keys()}
            total_w = sum(active_weights.values())
            if total_w > 0:
                norm_w = {k: w / total_w for k, w in active_weights.items()}
            else:
                norm_w = {k: 1.0 / len(predictions) for k in predictions.keys()}

            blended_val = sum(norm_w[k] * predictions[k] for k in predictions.keys())
            return round(blended_val, 2), "Ensemble", breakdown

        # 2. Specific single model prediction
        if target_key in predictions:
            val = predictions[target_key]
            formal_name = self.FORMAL_NAMES.get(target_key, target_key)
            return round(val, 2), formal_name, breakdown

        # Fallback to any available prediction
        first_key = next(iter(predictions.keys()))
        val = predictions[first_key]
        return round(val, 2), self.FORMAL_NAMES.get(first_key, first_key), breakdown


# Global singleton registry
registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    return registry
