from typing import Any

import joblib
import numpy as np
import os
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

from app.models.evaluation import ModelEvaluation
from app.models.experiment import Experiment
from app.models.model import TrainedModel
from app.models.ml_ready_dataset import MLReadyDataset
from app.services.data_engine.ingester import read_file


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


# ---------------------------------------------------------------------------
# Evaluation orchestration
# ---------------------------------------------------------------------------


class EvaluationError(Exception):
    pass


# Deterministic model priority for tie-breaking (lower index = higher priority).
# Mirrors the trainer's ordering so evaluation and training agree on best model.
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


def _model_order(problem_type: str) -> list[str]:
    if problem_type == "classification":
        return CLASSIFICATION_MODEL_ORDER
    return REGRESSION_MODEL_ORDER


def _default_primary_metric(problem_type: str) -> str:
    return "f1" if problem_type == "classification" else "r2"


def _default_secondary_metric(problem_type: str) -> str:
    return "accuracy" if problem_type == "classification" else "rmse"


def _averaging_strategy(problem_type: str) -> str | None:
    return "weighted" if problem_type == "classification" else None


def _resolve_primary_metric(problem_type: str, experiment_best_metric: str | None) -> str:
    """Respect an existing experiment-configured primary metric, else default."""
    if problem_type == "classification":
        valid = {"f1", "accuracy", "precision", "recall"}
        default = "f1"
    else:
        valid = {"r2", "mae", "mse", "rmse"}
        default = "r2"
    if experiment_best_metric and experiment_best_metric in valid:
        return experiment_best_metric
    return default


def select_best_model(
    results: list[dict[str, Any]], problem_type: str, primary_metric: str | None = None
) -> dict[str, Any]:
    """Deterministic best-model selection.

    Classification: primary = f1 (weighted, higher is better),
                    secondary = accuracy (higher is better).
    Regression:     primary = r2 (higher is better),
                    secondary = rmse (lower is better).
    Tie-break: predefined model priority order (deterministic).
    """
    pm = primary_metric or _default_primary_metric(problem_type)
    primary_reverse = True  # all supported primary metrics are higher-is-better
    secondary = _default_secondary_metric(problem_type)
    secondary_reverse = pm != secondary
    if secondary == "rmse":
        secondary_reverse = False  # rmse is lower-is-better
    else:
        secondary_reverse = True  # accuracy is higher-is-better
    model_order = _model_order(problem_type)

    def sort_key(r: dict[str, Any]) -> tuple:
        model_name = r.get("model_name", "")
        priority = model_order.index(model_name) if model_name in model_order else 999
        metrics = r.get("metrics") or {}
        if primary_reverse:
            pri_sort = -metrics.get(pm, -float("inf"))
        else:
            pri_sort = metrics.get(pm, float("inf"))
        if secondary_reverse:
            sec_sort = -metrics.get(secondary, -float("inf"))
        else:
            sec_sort = metrics.get(secondary, float("inf"))
        return (pri_sort, sec_sort, priority)

    ranked = sorted(results, key=sort_key)
    return ranked[0]


def rank_models(
    results: list[dict[str, Any]], problem_type: str, primary_metric: str | None = None
) -> list[dict[str, Any]]:
    """Return models ranked with the best first (deterministic)."""
    pm = primary_metric or _default_primary_metric(problem_type)
    secondary = _default_secondary_metric(problem_type)
    primary_reverse = True
    if secondary == "rmse":
        secondary_reverse = False
    else:
        secondary_reverse = True
    model_order = _model_order(problem_type)

    def sort_key(r: dict[str, Any]) -> tuple:
        model_name = r.get("model_name", "")
        priority = model_order.index(model_name) if model_name in model_order else 999
        metrics = r.get("metrics") or {}
        if primary_reverse:
            pri_sort = -metrics.get(pm, -float("inf"))
        else:
            pri_sort = metrics.get(pm, float("inf"))
        if secondary_reverse:
            sec_sort = -metrics.get(secondary, -float("inf"))
        else:
            sec_sort = metrics.get(secondary, float("inf"))
        return (pri_sort, sec_sort, priority)

    return sorted(results, key=sort_key)


def _load_test_split(ml_ready: MLReadyDataset, target_column: str):
    """Load the ML-ready CSV and return (X_test, y_test, feature_names)."""
    if not ml_ready.ml_ready_file_path or not _file_exists(ml_ready.ml_ready_file_path):
        raise EvaluationError("ML-ready dataset file is missing on disk")

    df = read_file(ml_ready.ml_ready_file_path)

    if "__split__" not in df.columns:
        raise EvaluationError(
            "ML-ready dataset is missing the __split__ indicator column"
        )

    if target_column not in df.columns:
        raise EvaluationError(
            f"Target column '{target_column}' not found in ML-ready dataset"
        )

    feature_names = [
        c for c in df.columns if c not in ("__split__", target_column)
    ]
    test_df = df[df["__split__"] == "test"].reset_index(drop=True)

    if len(test_df) == 0:
        raise EvaluationError("No test rows found in ML-ready dataset")

    X_test = test_df[feature_names]
    y_test = test_df[target_column]
    return X_test, y_test, feature_names


def _file_exists(path: str) -> bool:
    return bool(path) and os.path.exists(path)


def evaluate_experiment(
    db_session: Any,
    experiment: Experiment,
    current_user_id: int | None = None,
) -> dict[str, Any]:
    """Re-evaluate every trained model in an experiment.

    Metrics are recomputed by reloading each model artifact and running it over
    the experiment's held-out test split, so persisted evaluations are always
    authoritative and verify that artifacts are loadable.
    """
    if current_user_id is not None and experiment.owner_id != current_user_id:
        raise EvaluationError("Experiment access denied")

    ml_ready = experiment.ml_ready_dataset
    if not ml_ready:
        raise EvaluationError("Experiment has no ML-ready dataset")

    problem_type = experiment.problem_type or "classification"
    target_column = experiment.target_column
    if not target_column:
        raise EvaluationError("Experiment target_column is not set")

    primary_metric = _resolve_primary_metric(
        problem_type, getattr(experiment, "best_metric", None)
    )
    averaging = _averaging_strategy(problem_type)

    try:
        X_test, y_test, feature_names = _load_test_split(ml_ready, target_column)
    except EvaluationError:
        raise
    except Exception as e:
        raise EvaluationError(f"Failed to load ML-ready test data: {e}") from e

    # Clear any previous evaluations for this experiment so the endpoint is
    # idempotent (a fresh, authoritative evaluation on every call).
    db_session.query(ModelEvaluation).filter(
        ModelEvaluation.experiment_id == experiment.id
    ).delete(synchronize_session=False)
    db_session.commit()

    trained_models = (
        db_session.query(TrainedModel)
        .filter(TrainedModel.experiment_id == experiment.id)
        .order_by(TrainedModel.id)
        .all()
    )

    model_results: list[dict[str, Any]] = []
    for idx, tm in enumerate(trained_models):
        entry: dict[str, Any] = {
            "model_id": idx,
            "db_model_id": tm.id,
            "model_name": tm.name,
            "algorithm": tm.algorithm,
            "model_type": tm.model_type,
            "status": tm.status,
            "metrics": None,
            "primary_metric": primary_metric,
            "primary_metric_value": None,
            "averaging_strategy": averaging,
            "evaluation_status": "pending",
            "error_message": None,
            "trained_model_id": tm.id,
        }

        if tm.status != "trained" or not tm.model_path:
            entry["evaluation_status"] = "skipped"
            entry["error_message"] = (
                "Model was not trained successfully or artifact is missing"
            )
            _persist_evaluation(
                db_session, tm, experiment.id, entry, primary_metric, averaging
            )
            model_results.append(entry)
            continue

        try:
            model = joblib.load(tm.model_path)
            y_pred = model.predict(X_test)
            metrics = evaluate_model(y_test, y_pred, problem_type)
            entry["metrics"] = metrics
            entry["primary_metric_value"] = metrics.get(primary_metric)
            entry["evaluation_status"] = "completed"
        except Exception as e:
            entry["evaluation_status"] = "failed"
            entry["error_message"] = str(e)

        _persist_evaluation(
            db_session, tm, experiment.id, entry, primary_metric, averaging
        )
        model_results.append(entry)

    # --- Best model selection (deterministic) -----------------------------
    successful = [
        r
        for r in model_results
        if r["evaluation_status"] == "completed" and r["metrics"] and r["primary_metric_value"] is not None
    ]

    best_db_model_id: int | None = None
    best_metric = primary_metric
    best_score: float | None = None
    best_model_name: str | None = None
    best_index: int | None = None

    if successful:
        best_result = select_best_model(
            successful, problem_type, primary_metric=primary_metric
        )
        best_db_model_id = best_result["db_model_id"]
        best_index = best_result["model_id"]
        best_score = best_result["primary_metric_value"]
        best_model_name = best_result["model_name"]

    # Persist best-model selection on the experiment.
    if best_db_model_id is not None:
        experiment.best_model_id = best_db_model_id
        experiment.best_metric = best_metric
        experiment.best_score = best_score
        if experiment.status != "completed":
            experiment.status = "completed"
        experiment.error_message = None
    else:
        experiment.best_model_id = None
        experiment.best_metric = best_metric
        experiment.best_score = None
        experiment.error_message = "No models evaluated successfully"

    db_session.commit()
    db_session.refresh(experiment)

    best_db_id = experiment.best_model_id
    for r in model_results:
        r["is_best"] = r["db_model_id"] == best_db_id

    return {
        "experiment_id": experiment.id,
        "dataset_id": experiment.dataset_id,
        "name": experiment.name,
        "experiment_type": problem_type,
        "problem_type": problem_type,
        "target_column": target_column,
        "status": experiment.status,
        "primary_metric": primary_metric,
        "secondary_metric": _default_secondary_metric(problem_type),
        "averaging_strategy": averaging,
        "best_model_id": best_index,
        "best_db_model_id": best_db_model_id,
        "best_model_name": best_model_name,
        "best_metric": best_metric,
        "best_score": best_score,
        "error_message": experiment.error_message,
        "models": model_results,
    }


def _persist_evaluation(
    db_session: Any,
    tm: TrainedModel,
    experiment_id: int,
    entry: dict[str, Any],
    primary_metric: str,
    averaging: str | None,
) -> None:


    record = ModelEvaluation(
        experiment_id=experiment_id,
        trained_model_id=tm.id,
        metrics=entry.get("metrics"),
        primary_metric=primary_metric,
        primary_metric_value=entry.get("primary_metric_value"),
        averaging_strategy=averaging,
        evaluation_status=entry.get("evaluation_status", "pending"),
        error_message=entry.get("error_message"),
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    entry["evaluation_id"] = record.id


def get_evaluation_summary(
    db_session: Any, experiment: Experiment
) -> dict[str, Any]:
    """Return persisted evaluation results for an experiment.

    If no evaluations have been recorded yet, returns a summary with an empty
    evaluations list (callers decide whether to surface a 404).
    """


    problem_type = experiment.problem_type or "classification"
    primary_metric = _resolve_primary_metric(
        problem_type, getattr(experiment, "best_metric", None)
    )
    averaging = _averaging_strategy(problem_type)

    evals = (
        db_session.query(ModelEvaluation)
        .filter(ModelEvaluation.experiment_id == experiment.id)
        .order_by(ModelEvaluation.created_at.desc())
        .all()
    )

    trained_models = (
        db_session.query(TrainedModel)
        .filter(TrainedModel.experiment_id == experiment.id)
        .order_by(TrainedModel.id)
        .all()
    )
    tm_map = {tm.id: tm for tm in trained_models}
    best_db_id = experiment.best_model_id

    # Keep only the latest evaluation per trained model.
    seen: set[int] = set()
    evaluation_list: list[dict[str, Any]] = []
    for e in evals:
        if e.trained_model_id in seen:
            continue
        seen.add(e.trained_model_id)
        tm = tm_map.get(e.trained_model_id)
        evaluation_list.append(
            {
                "evaluation_id": e.id,
                "trained_model_id": e.trained_model_id,
                "model_id": _find_model_index(trained_models, e.trained_model_id),
                "model_name": tm.name if tm else None,
                "algorithm": tm.algorithm if tm else None,
                "model_type": tm.model_type if tm else None,
                "metrics": e.metrics,
                "primary_metric": e.primary_metric,
                "primary_metric_value": e.primary_metric_value,
                "averaging_strategy": e.averaging_strategy,
                "evaluation_status": e.evaluation_status,
                "error_message": e.error_message,
                "is_best": e.trained_model_id == best_db_id,
                "created_at": e.created_at,
            }
        )

    return {
        "experiment_id": experiment.id,
        "experiment_name": experiment.name,
        "problem_type": problem_type,
        "status": experiment.status,
        "primary_metric": primary_metric,
        "secondary_metric": _default_secondary_metric(problem_type),
        "averaging_strategy": averaging,
        "best_model_id": _find_model_index(trained_models, best_db_id),
        "best_db_model_id": best_db_id,
        "best_score": experiment.best_score,
        "evaluations": evaluation_list,
    }


def get_model_evaluation(
    db_session: Any, experiment: Experiment, model_index: int
) -> dict[str, Any]:
    """Return the latest persisted evaluation for a single model by index."""
    trained_models = (
        db_session.query(TrainedModel)
        .filter(TrainedModel.experiment_id == experiment.id)
        .order_by(TrainedModel.id)
        .all()
    )
    if model_index < 0 or model_index >= len(trained_models):
        raise EvaluationError("Model not found in this experiment")
    tm = trained_models[model_index]



    eval_record = (
        db_session.query(ModelEvaluation)
        .filter(
            ModelEvaluation.experiment_id == experiment.id,
            ModelEvaluation.trained_model_id == tm.id,
        )
        .order_by(ModelEvaluation.created_at.desc())
        .first()
    )

    problem_type = experiment.problem_type or "classification"
    primary_metric = _resolve_primary_metric(
        problem_type, getattr(experiment, "best_metric", None)
    )
    averaging = _averaging_strategy(problem_type)

    if eval_record is None:
        return {
            "experiment_id": experiment.id,
            "trained_model_id": tm.id,
            "model_id": model_index,
            "model_name": tm.name,
            "algorithm": tm.algorithm,
            "model_type": tm.model_type,
            "metrics": tm.metrics,
            "primary_metric": primary_metric,
            "primary_metric_value": tm.metrics.get(primary_metric) if tm.metrics else None,
            "averaging_strategy": averaging,
            "evaluation_status": "not_evaluated",
            "error_message": None,
            "is_best": tm.id == experiment.best_model_id,
            "message": (
                "No persisted evaluation found; showing training-time metrics. "
                "POST /evaluate to run an authoritative evaluation."
            ),
        }

    return {
        "experiment_id": experiment.id,
        "evaluation_id": eval_record.id,
        "trained_model_id": tm.id,
        "model_id": model_index,
        "model_name": tm.name,
        "algorithm": tm.algorithm,
        "model_type": tm.model_type,
        "metrics": eval_record.metrics,
        "primary_metric": eval_record.primary_metric or primary_metric,
        "primary_metric_value": eval_record.primary_metric_value,
        "averaging_strategy": eval_record.averaging_strategy or averaging,
        "evaluation_status": eval_record.evaluation_status,
        "error_message": eval_record.error_message,
        "is_best": tm.id == experiment.best_model_id,
        "evaluated_at": eval_record.created_at,
    }


def get_model_comparison(
    db_session: Any, experiment: Experiment
) -> dict[str, Any]:
    """Return models ranked by the experiment's primary metric."""


    problem_type = experiment.problem_type or "classification"
    primary_metric = _resolve_primary_metric(
        problem_type, getattr(experiment, "best_metric", None)
    )
    averaging = _averaging_strategy(problem_type)
    secondary = _default_secondary_metric(problem_type)

    trained_models = (
        db_session.query(TrainedModel)
        .filter(TrainedModel.experiment_id == experiment.id)
        .order_by(TrainedModel.id)
        .all()
    )

    model_order = _model_order(problem_type)

    # Prefer persisted evaluations; fall back to training-time metrics.
    eval_records = (
        db_session.query(ModelEvaluation)
        .filter(ModelEvaluation.experiment_id == experiment.id)
        .order_by(ModelEvaluation.created_at.desc())
        .all()
    )
    eval_by_tm: dict[int, ModelEvaluation] = {}
    for e in eval_records:
        if e.trained_model_id not in eval_by_tm:
            eval_by_tm[e.trained_model_id] = e

    results: list[dict[str, Any]] = []
    for idx, tm in enumerate(trained_models):
        if tm.id in eval_by_tm and eval_by_tm[tm.id].metrics:
            metrics = eval_by_tm[tm.id].metrics
            status = eval_by_tm[tm.id].evaluation_status
        else:
            metrics = tm.metrics if tm.metrics else {}
            status = tm.status
        results.append(
            {
                "model_id": idx,
                "db_model_id": tm.id,
                "model_name": tm.name,
                "algorithm": tm.algorithm,
                "model_type": tm.model_type,
                "status": status,
                "metrics": metrics,
                "primary_metric_value": metrics.get(primary_metric),
                "model_order_priority": (
                    model_order.index(tm.name) if tm.name in model_order else 999
                ),
            }
        )

    ranked = rank_models(results, problem_type, primary_metric=primary_metric)
    best_db_id = experiment.best_model_id

    ranked_response: list[dict[str, Any]] = []
    for rank, r in enumerate(ranked, start=1):
        ranked_response.append(
            {
                "rank": rank,
                "trained_model_id": r["db_model_id"],
                "model_id": r["model_id"],
                "model_name": r["model_name"],
                "algorithm": r["algorithm"],
                "model_type": r["model_type"],
                "status": r["status"],
                "metrics": r["metrics"],
                "primary_metric": primary_metric,
                "primary_metric_value": r["primary_metric_value"],
                "is_best": r["db_model_id"] == best_db_id,
            }
        )

    return {
        "experiment_id": experiment.id,
        "experiment_name": experiment.name,
        "problem_type": problem_type,
        "primary_metric": primary_metric,
        "secondary_metric": secondary,
        "averaging_strategy": averaging,
        "ranked_models": ranked_response,
    }


def _find_model_index(trained_models: list[TrainedModel], best_db_id: int | None) -> int | None:
    if best_db_id is None:
        return None
    for idx, tm in enumerate(trained_models):
        if tm.id == best_db_id:
            return idx
    return None
