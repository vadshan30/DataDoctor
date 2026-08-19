"""Model explainability service for extracting feature importance.

Provides deterministic extraction of feature importance from trained models
using available methods like feature_importances_ (tree-based) and coef_ (linear).
"""

from typing import Any

import joblib
import numpy as np

class ExplainabilityError(Exception):
    """Raised when explainability extraction fails."""

    pass


def get_feature_importance(
    model_path: str, algorithm: str, feature_names: list[str] | None = None
) -> dict[str, Any] | None:
    """Extract feature importance from a trained model.

    Supports:
    - Tree-based models (RandomForest, DecisionTree): uses feature_importances_
    - Linear models (LogisticRegression, LinearRegression): uses coef_

    Args:
        model_path: Path to the joblib-saved model
        algorithm: Name of the algorithm (e.g., "RandomForestClassifier")

    Returns:
        Dictionary with keys:
        - type: "tree" or "linear"
        - features: list of FeatureImportance objects
        or None if feature importance is not available for this algorithm.
    """
    try:
        model = joblib.load(model_path)
    except Exception as e:
        raise ExplainabilityError(f"Failed to load model from {model_path}: {e}")

    # Try tree-based feature importance
    if hasattr(model, "feature_importances_"):
        return _extract_tree_importance(model, algorithm, feature_names)

    # Try linear coefficients
    if hasattr(model, "coef_"):
        return _extract_linear_importance(model, algorithm, feature_names)

    # Feature importance not available
    return None


def _extract_tree_importance(
    model: Any, algorithm: str, feature_names: list[str] | None = None
) -> dict[str, Any]:
    """Extract feature importance from tree-based models."""
    importances = model.feature_importances_
    names = feature_names or [f"Feature_{idx}" for idx in range(len(importances))]

    # Create FeatureImportance objects
    features = []
    for idx, importance in enumerate(importances):
        features.append(
            {
                "feature_name": names[idx] if idx < len(names) else f"Feature_{idx}",
                "importance_value": float(importance),
                "normalized_importance": float(importance) / float(np.sum(importances))
                if np.sum(importances) > 0
                else 0.0,
                "rank": 0,  # Will set ranks after sorting
            }
        )

    # Sort by importance descending and assign ranks
    features_sorted = sorted(features, key=lambda x: x["importance_value"], reverse=True)
    for rank, feature in enumerate(features_sorted, start=1):
        feature["rank"] = rank

    return {
        "type": "tree",
        "features": features_sorted,
        "algorithm": algorithm,
    }


def _extract_linear_importance(
    model: Any, algorithm: str, feature_names: list[str] | None = None
) -> dict[str, Any]:
    """Extract feature importance from linear models."""
    coef = model.coef_
    
    # Handle multi-class case where coef_ is 2D
    if len(coef.shape) > 1:
        # Take the absolute mean across classes
        coef = np.abs(coef).mean(axis=0)
    else:
        coef = np.abs(coef)

    names = feature_names or [f"Feature_{idx}" for idx in range(len(coef))]

    # Create FeatureImportance objects
    features = []
    for idx, importance in enumerate(coef):
        features.append(
            {
                "feature_name": names[idx] if idx < len(names) else f"Feature_{idx}",
                "importance_value": float(importance),
                "normalized_importance": float(importance) / float(np.sum(coef))
                if np.sum(coef) > 0
                else 0.0,
                "rank": 0,  # Will set ranks after sorting
            }
        )

    # Sort by importance descending and assign ranks
    features_sorted = sorted(features, key=lambda x: x["importance_value"], reverse=True)
    for rank, feature in enumerate(features_sorted, start=1):
        feature["rank"] = rank

    return {
        "type": "linear",
        "features": features_sorted,
        "algorithm": algorithm,
    }
