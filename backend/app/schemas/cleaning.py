from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CleaningOperation(BaseModel):
    operation: str
    column: str | None = None
    affected_rows: int
    strategy: str | None = None
    replacement_value: Any | None = None
    detail: str | None = None


class CleaningResultResponse(BaseModel):
    cleaned_dataset_id: int = Field(validation_alias="id")
    dataset_id: int
    cleaning_status: str
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    missing_values_handled: int
    duplicates_removed: int
    cleaning_operations: list[CleaningOperation]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CleaningResultListResponse(BaseModel):
    cleaned_datasets: list[CleaningResultResponse]
    total: int


class ErrorResponse(BaseModel):
    detail: str
