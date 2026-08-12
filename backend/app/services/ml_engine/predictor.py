import os
from typing import Any

import joblib
import numpy as np
import pandas as pd
import warnings
from contextlib import contextmanager

from app.models.prediction import PredictionRecord
from app.models.model import TrainedModel


class PredictionError(Exception):
    pass


@contextmanager
def _suppress_feature_names_warning():
    """The model was trained on a column-named DataFrame but prediction passes a
    numpy array from the fitted preprocessor; the resulting sklearn warning is
    benign and would only clutter logs / test output."""
    with warnings.catch_warnings():
        warnings.simplefilter(
            "ignore", category=UserWarning
        )
        yield


def _to_jsonable(value: Any) -> Any:
    """Convert numpy/pandas scalars to JSON-serializable Python types."""
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def _required_feature_columns(ml_ready) -> list[str]:
    """Original (pre-transform) feature columns expected as model input."""
    cols: list[str] = list(ml_ready.numeric_columns or [])
    cols += list(ml_ready.categorical_columns or [])
    # De-duplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in cols:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def _validate_features(
    features: dict[str, Any],
    required_columns: list[str],
    target_column: str | None,
) -> None:
    """Validate that the input has exactly the required feature columns."""
    input_keys = set(features.keys())
    required_set = set(required_columns)

    if target_column and target_column in input_keys:
        raise PredictionError(
            f"'{target_column}' is the target column and must not be supplied as a feature"
        )

    missing = [c for c in required_columns if c not in input_keys]
    if missing:
        raise PredictionError(
            f"Missing required feature(s): {', '.join(missing)}"
        )

    unexpected = [k for k in features.keys() if k not in required_set]
    if unexpected:
        raise PredictionError(
            f"Unexpected feature(s) not used during training: {', '.join(sorted(unexpected))}"
        )


def _validate_feature_datatypes(
    features: dict[str, Any], numeric_columns: list[str]
) -> None:
    """Best-effort type validation for numeric features."""
    for col in numeric_columns:
        if col not in features:
            continue
        value = features[col]
        if value is None:
            continue
        try:
            float(value)
        except (TypeError, ValueError):
            raise PredictionError(
                f"Feature '{col}' must be numeric, got {type(value).__name__}"
            )


def load_model_and_preprocessor(
    db_session: Any, trained_model_id: int
) -> tuple[TrainedModel, Any, Any]:
    """Load the trained model artifact and its fitted preprocessing pipeline."""
    trained_model = (
        db_session.query(TrainedModel)
        .filter(TrainedModel.id == trained_model_id)
        .first()
    )
    if not trained_model:
        raise PredictionError("Trained model not found")

    if trained_model.status != "trained":
        raise PredictionError(
            f"Model is not ready for prediction (status={trained_model.status})"
        )

    if not trained_model.model_path or not os.path.exists(trained_model.model_path):
        raise PredictionError("Model artifact is missing on disk")

    ml_ready = trained_model.experiment.ml_ready_dataset if trained_model.experiment else None
    if not ml_ready:
        raise PredictionError("No ML-ready dataset associated with this model")

    if not ml_ready.preprocessor_path or not os.path.exists(
        ml_ready.preprocessor_path
    ):
        raise PredictionError(
            "A fitted preprocessing pipeline is required for prediction but was not persisted"
        )

    try:
        model = joblib.load(trained_model.model_path)
    except Exception as e:
        raise PredictionError("Failed to load model artifact") from e

    try:
        preprocessor = joblib.load(ml_ready.preprocessor_path)
    except Exception as e:
        raise PredictionError("Failed to load preprocessing pipeline") from e

    return trained_model, model, (ml_ready, preprocessor)


def predict_single(
    db_session: Any,
    trained_model_id: int,
    features: dict[str, Any],
    model_index: int | None = None,
) -> dict[str, Any]:
    trained_model, model, (ml_ready, preprocessor) = load_model_and_preprocessor(
        db_session, trained_model_id
    )

    target_column = ml_ready.target_column
    required_columns = _required_feature_columns(ml_ready)
    numeric_columns = list(ml_ready.numeric_columns or [])
    problem_type = trained_model.model_type or "unknown"

    _validate_features(features, required_columns, target_column)
    _validate_feature_datatypes(features, numeric_columns)

    input_df = pd.DataFrame([features], columns=required_columns)
    try:
        transformed = preprocessor.transform(input_df)
    except Exception as e:
        raise PredictionError(f"Failed to preprocess input features: {e}") from e

    try:
        with _suppress_feature_names_warning():
            prediction = model.predict(transformed)
    except Exception as e:
        raise PredictionError(f"Prediction failed: {e}") from e

    prediction_value = _to_jsonable(prediction[0]) if len(prediction) > 0 else None
    if isinstance(prediction_value, np.ndarray):
        prediction_value = prediction_value.tolist()

    result = {
        "model_id": model_index if model_index is not None else trained_model.id,
        "trained_model_id": trained_model.id,
        "model_name": trained_model.name,
        "algorithm": trained_model.algorithm,
        "model_type": trained_model.model_type,
        "problem_type": problem_type,
        "prediction": prediction_value,
    }
    return result


def predict_batch(
    db_session: Any,
    trained_model_id: int,
    rows: list[dict[str, Any]],
    model_index: int | None = None,
) -> dict[str, Any]:
    if not rows:
        raise PredictionError("No input rows provided")

    trained_model, model, (ml_ready, preprocessor) = load_model_and_preprocessor(
        db_session, trained_model_id
    )

    target_column = ml_ready.target_column
    required_columns = _required_feature_columns(ml_ready)
    numeric_columns = list(ml_ready.numeric_columns or [])
    problem_type = trained_model.model_type or "unknown"

    for i, row in enumerate(rows):
        _validate_features(row, required_columns, target_column)
        _validate_feature_datatypes(row, numeric_columns)

    input_df = pd.DataFrame(rows, columns=required_columns)
    try:
        transformed = preprocessor.transform(input_df)
    except Exception as e:
        raise PredictionError(f"Failed to preprocess input features: {e}") from e

    try:
        with _suppress_feature_names_warning():
            predictions = model.predict(transformed)
    except Exception as e:
        raise PredictionError(f"Prediction failed: {e}") from e

    pred_list = [_to_jsonable(p) for p in predictions.tolist()]

    return {
        "model_id": model_index if model_index is not None else trained_model.id,
        "trained_model_id": trained_model.id,
        "model_name": trained_model.name,
        "algorithm": trained_model.algorithm,
        "model_type": trained_model.model_type,
        "problem_type": problem_type,
        "predictions": pred_list,
    }


def save_prediction_record(
    db_session: Any,
    experiment_id: int,
    trained_model_id: int | None,
    input_data: dict[str, Any] | None,
    prediction: dict[str, Any] | None,
    model_type: str | None,
) -> Any:
    record = PredictionRecord(
        experiment_id=experiment_id,
        trained_model_id=trained_model_id,
        input_data=input_data,
        prediction=prediction,
        model_type=model_type,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record
