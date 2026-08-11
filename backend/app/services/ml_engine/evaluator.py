from typing import Any

import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)


def evaluate_classification(y_true, y_pred) -> dict[str, Any]:
    """Compute deterministic classification metrics.

    Uses weighted averaging for precision/recall/F1 to support multiclass
    targets safely.  ``zero_division=0`` prevents crashes when a class has
    no predicted samples.
    """
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)

    unique_labels = np.unique(np.concatenate([y_true_arr, y_pred_arr]))

    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true_arr, y_pred_arr)),
        "precision": float(
            precision_score(
                y_true_arr, y_pred_arr, average="weighted", zero_division=0
            )
        ),
        "recall": float(
            recall_score(
                y_true_arr, y_pred_arr, average="weighted", zero_division=0
            )
        ),
        "f1": float(
            f1_score(
                y_true_arr, y_pred_arr, average="weighted", zero_division=0
            )
        ),
    }

    # Confusion matrix — only meaningful when there are few enough labels
    if len(unique_labels) <= 20:
        cm = confusion_matrix(y_true_arr, y_pred_arr, labels=unique_labels)
        metrics["confusion_matrix"] = cm.tolist()
        metrics["confusion_matrix_labels"] = [str(l) for l in unique_labels]

    return metrics


def evaluate_regression(y_true, y_pred) -> dict[str, Any]:
    """Compute deterministic regression metrics."""
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)

    mse = float(mean_squared_error(y_true_arr, y_pred_arr))

    return {
        "mae": float(mean_absolute_error(y_true_arr, y_pred_arr)),
        "mse": mse,
        "rmse": float(np.sqrt(mse)),
        "r2": float(r2_score(y_true_arr, y_pred_arr)),
    }


def evaluate_model(y_true, y_pred, problem_type: str) -> dict[str, Any]:
    if problem_type == "classification":
        return evaluate_classification(y_true, y_pred)
    return evaluate_regression(y_true, y_pred)
