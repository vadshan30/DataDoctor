from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.cleaning import CleaningOperation


class FeatureEngineeringOperation(BaseModel):
    operation: str
    column: str | None = None
    new_features: list[str] | None = None
    strategy: str | None = None
    affected_rows: int | None = None
    replacement_value: Any | None = None
    detail: str | None = None


class EngineeringResultResponse(BaseModel):
    engineered_dataset_id: int = Field(validation_alias="id")
    dataset_id: int
    cleaned_dataset_id: int | None = None
    engineering_status: str
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    features_added: int
    features_removed: int
    new_feature_names: list[str] = Field(default_factory=list, validation_alias="feature_names")
    feature_engineering_operations: list[FeatureEngineeringOperation]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EngineeringResultListResponse(BaseModel):
    engineered_datasets: list[EngineeringResultResponse]
    total: int


class ErrorResponse(BaseModel):
    detail: str
