from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvaluationMetric(BaseModel):
    name: str
    value: float
    higher_is_better: bool = True


class EvaluationResult(BaseModel):
    experiment_id: int
    trained_model_id: int
    model_id: int
    model_name: str
    algorithm: str
    model_type: str
    metrics: dict[str, Any] | None = None
    primary_metric: str | None = None
    primary_metric_value: float | None = None
    averaging_strategy: str | None = None
    evaluation_status: str
    error_message: str | None = None
    is_best: bool = False
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ModelEvaluationResponse(BaseModel):
    evaluation_id: int
    experiment_id: int
    trained_model_id: int
    model_name: str
    algorithm: str
    model_type: str
    metrics: dict[str, Any] | None = None
    primary_metric: str | None = None
    primary_metric_value: float | None = None
    averaging_strategy: str | None = None
    evaluation_status: str
    error_message: str | None = None
    is_best: bool = False
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RankedModelResponse(BaseModel):
    rank: int
    trained_model_id: int
    model_id: int
    model_name: str
    algorithm: str
    model_type: str
    status: str
    metrics: dict[str, Any] | None = None
    primary_metric: str | None = None
    primary_metric_value: float | None = None
    is_best: bool = False
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ModelComparisonResponse(BaseModel):
    experiment_id: int
    experiment_name: str
    problem_type: str
    primary_metric: str
    secondary_metric: str | None = None
    averaging_strategy: str | None = None
    evaluation_timestamp: datetime
    ranked_models: list[RankedModelResponse]
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EvaluationSummaryResponse(BaseModel):
    experiment_id: int
    experiment_name: str
    problem_type: str
    status: str
    primary_metric: str | None = None
    averaging_strategy: str | None = None
    best_model_id: int | None = None
    best_model_name: str | None = None
    best_score: float | None = None
    evaluations: list[ModelEvaluationResponse]
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ErrorResponse(BaseModel):
    detail: str
