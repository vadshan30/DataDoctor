from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExperimentCreateRequest(BaseModel):
    ml_ready_dataset_id: int = Field(..., gt=0)
    experiment_name: str = Field(..., min_length=1, max_length=255)
    target_column: str = Field(..., min_length=1)
    problem_type: str = Field(..., pattern="^(classification|regression)$")

    @field_validator("experiment_name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if v is None or v.strip() == "":
            raise ValueError("experiment_name must not be empty")
        return v

    @field_validator("target_column")
    @classmethod
    def _validate_target(cls, v: str) -> str:
        if v is None or v.strip() == "":
            raise ValueError("target_column must not be empty")
        return v


class ModelResultResponse(BaseModel):
    model_id: int = Field(validation_alias="id")
    model_name: str
    algorithm: str
    model_type: str
    status: str
    metrics: dict[str, Any] | None = None
    hyperparameters: dict[str, Any] | None = None
    training_rows: int
    validation_rows: int
    feature_count: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ExperimentResponse(BaseModel):
    experiment_id: int = Field(validation_alias="id")
    dataset_id: int
    dataset_name: str | None = None
    ml_ready_dataset_id: int | None = None
    name: str
    experiment_type: str
    problem_type: str
    target_column: str | None = None
    test_size: float
    random_state: int
    status: str
    best_model_id: int | None = None
    best_metric: str | None = None
    best_score: float | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    models: list[ModelResultResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ExperimentListResponse(BaseModel):
    experiments: list[ExperimentResponse]
    total: int


class BestModelResponse(BaseModel):
    experiment_id: int
    model_id: int
    model_name: str
    algorithm: str
    model_type: str
    problem_type: str
    metrics: dict[str, Any] | None = None
    hyperparameters: dict[str, Any] | None = None
    training_rows: int
    validation_rows: int
    feature_count: int
    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    detail: str
