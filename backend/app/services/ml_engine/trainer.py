import os
import time
import uuid
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from app.core.config import settings
from app.core.database import get_db
from app.models.ml_ready_dataset import MLReadyDataset
from app.models.experiment import Experiment
from app.models.model import TrainedModel
from app.services.data_engine.ingester import DataIngestionError, read_file
from app.services.ml_engine.evaluator import evaluate_model

RANDOM_STATE = 42


class ExperimentError(Exception):
    pass


CLASSIFICATION_MODELS: dict[str, Any] = {
    "LogisticRegression": lambda: LogisticRegression(
        random_state=RANDOM_STATE, max_iter=1000
    ),
    "DecisionTreeClassifier": lambda: DecisionTreeClassifier(
        random_state=RANDOM_STATE
    ),
    "RandomForestClassifier": lambda: RandomForestClassifier(
        random_state=RANDOM_STATE, n_estimators=100
    ),
}

REGRESSION_MODELS: dict[str, Any] = {
    "LinearRegression": lambda: LinearRegression(),
    "DecisionTreeRegressor": lambda: DecisionTreeRegressor(
        random_state=RANDOM_STATE
    ),
    "RandomForestRegressor": lambda: RandomForestRegressor(
        random_state=RANDOM_STATE, n_estimators=100
    ),
}

# Deterministic model priority for tie-breaking (lower index = higher priority)
CLASSIFICATION_MODEL_ORDER = [
    "RandomForestClassifier",
    "LogisticRegression",
    "DecisionTreeClassifier",
]

REGRESSION_MODEL_ORDER = [
    "RandomForestRegressor",
    "LinearRegression",
    "DecisionTreeRegressor",
]


def _get_model_registry(problem_type: str) -> dict[str, Any]:
    if problem_type == "classification":
        return CLASSIFICATION_MODELS
    if problem_type == "regression":
        return REGRESSION_MODELS
    raise ExperimentError(f"Unsupported problem type: {problem_type}")


def _get_model_order(problem_type: str) -> list[str]:
    if problem_type == "classification":
        return CLASSIFICATION_MODEL_ORDER
    return REGRESSION_MODEL_ORDER


def _infer_problem_type(y: pd.Series) -> str:
    """Deterministic problem-type inference.

    * Boolean targets → classification
    * Non-numeric targets → classification
    * Numeric targets with few unique values (≤ 20) → classification
    * Otherwise → regression
    """
    if y.dtype == bool:
        return "classification"
    if not pd.api.types.is_numeric_dtype(y):
        return "classification"
    unique_count = y.nunique()
    if unique_count <= 20:
        return "classification"
    return "regression"


def _validate_ml_ready_dataset(ml_ready: MLReadyDataset, target_column: str) -> None:
    if not os.path.exists(ml_ready.ml_ready_file_path):
        raise ExperimentError("ML-ready dataset file is missing on disk")

    if target_column not in ml_ready.feature_names and target_column not in (
        ml_ready.target_column
    ):
        if target_column != ml_ready.target_column:
            raise ExperimentError(
                f"Target column '{target_column}' not found in ML-ready dataset"
            )


def _load_ml_ready_data(ml_ready: MLReadyDataset, target_column: str):
    """Load the ML-ready CSV and split into train/test feature matrices.

    Returns ``(X_train, X_test, y_train, y_test, feature_names)``.
    The ``__split__`` column and target column are excluded from features.
    """
    df = read_file(ml_ready.ml_ready_file_path)

    if "__split__" not in df.columns:
        raise ExperimentError(
            "ML-ready dataset is missing the __split__ indicator column"
        )

    if target_column not in df.columns:
        raise ExperimentError(
            f"Target column '{target_column}' not found in ML-ready dataset"
        )

    feature_names = [
        c for c in df.columns if c not in ("__split__", target_column)
    ]

    train_df = df[df["__split__"] == "train"].reset_index(drop=True)
    test_df = df[df["__split__"] == "test"].reset_index(drop=True)

    if len(train_df) == 0:
        raise ExperimentError("No training rows found in ML-ready dataset")
    if len(test_df) == 0:
        raise ExperimentError("No test rows found in ML-ready dataset")

    X_train = train_df[feature_names]
    X_test = test_df[feature_names]
    y_train = train_df[target_column]
    y_test = test_df[target_column]

    return X_train, X_test, y_train, y_test, feature_names


def _save_model_artifact(model, model_name: str, experiment_id: int) -> str:
    os.makedirs(settings.MODEL_DIR, exist_ok=True)
    filename = f"experiment_{experiment_id}_{model_name}_{uuid.uuid4().hex}.joblib"
    path = os.path.join(settings.MODEL_DIR, filename)
    joblib.dump(model, path)
    return path


def _select_best_model(
    results: list[dict[str, Any]], problem_type: str
) -> dict[str, Any]:
    """Deterministic best-model selection.

    Classification: primary = f1 (weighted, higher is better),
                    secondary = accuracy (higher is better).
    Regression:     primary = r2 (higher is better),
                    secondary = rmse (lower is better).
    Tie-break: predefined model priority order.
    """
    if problem_type == "classification":
        primary_key = "f1"
        primary_reverse = True
        secondary_key = "accuracy"
        secondary_reverse = True
    else:
        primary_key = "r2"
        primary_reverse = True
        secondary_key = "rmse"
        secondary_reverse = False

    model_order = _get_model_order(problem_type)

    def sort_key(r: dict[str, Any]) -> tuple:
        model_name = r["model_name"]
        priority = model_order.index(model_name) if model_name in model_order else 999
        pri_val = r["metrics"].get(primary_key, -float("inf") if primary_reverse else float("inf"))
        sec_val = r["metrics"].get(secondary_key, -float("inf") if secondary_reverse else float("inf"))
        # For reverse=False (minimize), negate to sort ascending
        if primary_reverse:
            pri_sort = -pri_val
        else:
            pri_sort = pri_val
        if secondary_reverse:
            sec_sort = -sec_val
        else:
            sec_sort = sec_val
        return (pri_sort, sec_sort, priority)

    ranked = sorted(results, key=sort_key)
    return ranked[0]


def run_experiment(
    db_session: Any,
    dataset_id: int,
    ml_ready_dataset_id: int,
    experiment_name: str,
    target_column: str,
    problem_type: str,
    test_size: float = 0.20,
    random_state: int = 42,
) -> dict[str, Any]:
    from app.models.user import User  # local import to avoid circular

    # --- Validate ML-ready dataset belongs to this dataset -----------------
    ml_ready = (
        db_session.query(MLReadyDataset)
        .filter(
            MLReadyDataset.id == ml_ready_dataset_id,
            MLReadyDataset.dataset_id == dataset_id,
        )
        .first()
    )
    if not ml_ready:
        raise ExperimentError("ML-ready dataset not found or does not belong to this dataset")

    dataset = ml_ready.dataset
    owner_id = dataset.owner_id

    # --- Validate target column -------------------------------------------
    _validate_ml_ready_dataset(ml_ready, target_column)

    # --- Load data and split train/test -----------------------------------
    try:
        X_train, X_test, y_train, y_test, feature_names = _load_ml_ready_data(
            ml_ready, target_column
        )
    except ExperimentError:
        raise
    except Exception as e:
        raise ExperimentError(f"Failed to load ML-ready data: {e}") from e

    # --- Validate sufficient data -----------------------------------------
    if len(X_train) < 2:
        raise ExperimentError(
            f"Insufficient training rows ({len(X_train)}) for model training"
        )
    if len(X_test) < 1:
        raise ExperimentError(
            f"Insufficient test rows ({len(X_test)}) for model evaluation"
        )

    # --- Determine / validate problem type --------------------------------
    if problem_type is None:
        problem_type = _infer_problem_type(y_train)

    if problem_type not in ("classification", "regression"):
        raise ExperimentError(
            f"Invalid problem_type '{problem_type}'. Must be 'classification' or 'regression'."
        )

    # --- Validate target for classification (at least 2 classes) ----------
    if problem_type == "classification":
        unique_classes = y_train.nunique()
        if unique_classes < 2:
            raise ExperimentError(
                f"Target column '{target_column}' has only {unique_classes} class(es); "
                "at least 2 classes are required for classification."
            )

    # --- Create experiment record (status = running) ----------------------
    experiment = Experiment(
        name=experiment_name,
        description=None,
        experiment_type=problem_type,
        problem_type=problem_type,
        target_column=target_column,
        test_size=test_size,
        random_state=random_state,
        dataset_id=dataset_id,
        owner_id=owner_id,
        ml_ready_dataset_id=ml_ready_dataset_id,
        status="running",
    )
    db_session.add(experiment)
    db_session.commit()
    db_session.refresh(experiment)

    model_registry = _get_model_registry(problem_type)
    model_order = _get_model_order(problem_type)

    trained_results: list[dict[str, Any]] = []
    trained_models: list[TrainedModel] = []

    overall_start = time.time()

    for model_name in model_order:
        if model_name not in model_registry:
            continue

        model_factory = model_registry[model_name]
        model_start = time.time()
        model_status = "pending"
        metrics: dict[str, Any] = {}
        hyperparameters: dict[str, Any] = {}
        model_path: str | None = None
        error_msg: str | None = None

        try:
            model = model_factory()

            # Record hyperparameters
            hyperparameters = model.get_params()

            model.fit(X_train, y_train)

            y_pred = model.predict(X_test)
            metrics = evaluate_model(y_test, y_pred, problem_type)

            model_status = "trained"
            model_path = _save_model_artifact(
                model, model_name, experiment.id
            )

        except Exception as e:
            model_status = "failed"
            error_msg = str(e)

        training_duration = time.time() - model_start

        trained_model = TrainedModel(
            name=model_name,
            model_type=problem_type,
            algorithm=model_name,
            status=model_status,
            metrics=metrics if metrics else None,
            parameters=None,
            hyperparameters=hyperparameters if hyperparameters else None,
            model_path=model_path,
            training_rows=len(X_train),
            validation_rows=len(X_test),
            feature_count=len(feature_names),
            experiment_id=experiment.id,
        )
        db_session.add(trained_model)
        db_session.commit()
        db_session.refresh(trained_model)

        result_entry: dict[str, Any] = {
            "model_id": len(trained_results),
            "db_model_id": trained_model.id,
            "model_name": model_name,
            "algorithm": model_name,
            "model_type": problem_type,
            "status": model_status,
            "metrics": metrics if metrics else None,
            "hyperparameters": hyperparameters if hyperparameters else None,
            "training_rows": len(X_train),
            "validation_rows": len(X_test),
            "feature_count": len(feature_names),
            "training_duration": training_duration,
        }
        if error_msg:
            result_entry["error"] = error_msg
        trained_results.append(result_entry)

        if model_path:
            trained_models.append(trained_model)

    # --- Select best model ------------------------------------------------
    successful_results = [
        r for r in trained_results if r["status"] == "trained" and r["metrics"]
    ]

    best_score: float | None = None
    best_metric: str | None = None
    best_model_id: int | None = None

    if successful_results:
        best_result = _select_best_model(successful_results, problem_type)
        best_db_model_id = best_result["db_model_id"]
        best_model_id = best_result["model_id"]
        best_metric_key = "f1" if problem_type == "classification" else "r2"
        best_metric = best_metric_key
        best_score = best_result["metrics"][best_metric_key]
    else:
        experiment.error_message = "No models trained successfully"
        db_session.commit()
        clean_results = [
            {k: v for k, v in r.items() if k != "db_model_id"}
            for r in trained_results
        ]
        return {
            "experiment_id": experiment.id,
            "dataset_id": dataset_id,
            "ml_ready_dataset_id": ml_ready_dataset_id,
            "name": experiment.name,
            "experiment_type": problem_type,
            "problem_type": problem_type,
            "target_column": target_column,
            "test_size": test_size,
            "random_state": random_state,
            "status": experiment.status,
            "best_model_id": None,
            "best_metric": None,
            "best_score": None,
            "error_message": "No models trained successfully",
            "models": clean_results,
        }

    # --- Update experiment ------------------------------------------------
    experiment.status = "completed"
    experiment.best_model_id = best_db_model_id
    experiment.best_metric = best_metric
    experiment.best_score = best_score
    from datetime import datetime
    experiment.completed_at = datetime.utcnow()
    experiment.error_message = None

    db_session.commit()
    db_session.refresh(experiment)

    trained_results = [
        {k: v for k, v in r.items() if k != "db_model_id"}
        for r in trained_results
    ]

    total_duration = time.time() - overall_start

    return {
        "experiment_id": experiment.id,
        "dataset_id": dataset_id,
        "ml_ready_dataset_id": ml_ready_dataset_id,
        "name": experiment.name,
        "experiment_type": problem_type,
        "problem_type": problem_type,
        "target_column": target_column,
        "test_size": test_size,
        "random_state": random_state,
        "status": experiment.status,
        "best_model_id": best_model_id,
        "best_metric": best_metric,
        "best_score": best_score,
        "error_message": experiment.error_message,
        "training_rows": len(X_train),
        "validation_rows": len(X_test),
        "feature_names": feature_names,
        "feature_count": len(feature_names),
        "models": trained_results,
        "total_training_duration": total_duration,
    }
