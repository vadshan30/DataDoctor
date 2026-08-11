from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PrepareRequest(BaseModel):
    target_column: str = Field(..., min_length=1)
    test_size: float = Field(default=0.20, ge=0.1, le=0.5)
    random_state: int = Field(default=42)

    @field_validator("target_column")
    @classmethod
    def _validate_target_column(cls, v: str) -> str:
        if v is None or v.strip() == "":
            raise ValueError("target_column must not be empty")
        return v


class MLReadyDatasetResponse(BaseModel):
    ml_ready_dataset_id: int = Field(validation_alias="id")
    dataset_id: int
    source_dataset_type: str
    target_column: str
    rows_before: int
    rows_after: int
    train_rows: int
    test_rows: int
    original_feature_count: int
    processed_feature_count: int
    numeric_columns: list[str]
    categorical_columns: list[str]
    feature_names: list[str]
    test_size: float
    random_state: int
    preprocessing_operations: list[dict[str, Any]]
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MLReadyDatasetListResponse(BaseModel):
    prepared_datasets: list[MLReadyDatasetResponse]
    total: int


class ErrorResponse(BaseModel):
    detail: str
