from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    features: dict[str, Any] = Field(..., min_length=1)


class BatchPredictionRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., min_length=1)


class FeatureValidationError(BaseModel):
    missing_features: list[str] = Field(default_factory=list)
    unexpected_features: list[str] = Field(default_factory=list)


class PredictionResult(BaseModel):
    model_id: int
    model_name: str
    algorithm: str
    model_type: str
    problem_type: str
    prediction: Any
    input_data: dict[str, Any] | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BatchPredictionResult(BaseModel):
    model_id: int
    model_name: str
    algorithm: str
    model_type: str
    problem_type: str
    predictions: list[Any]
    input_data: list[dict[str, Any]] | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PredictionRecordResponse(BaseModel):
    id: int = Field(validation_alias="id")
    experiment_id: int
    trained_model_id: int | None = None
    model_type: str | None = None
    input_data: dict[str, Any] | None = None
    prediction: dict[str, Any] | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PredictionRecordListResponse(BaseModel):
    predictions: list[PredictionRecordResponse]
    total: int


class ErrorResponse(BaseModel):
    detail: str
