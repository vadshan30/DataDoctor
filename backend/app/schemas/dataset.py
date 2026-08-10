from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

class DatasetResponse(BaseModel):
    dataset_id: int = Field(validation_alias="id")
    name: str
    description: str | None = None
    file_path: str
    file_type: str
    file_size: int
    row_count: int = Field(validation_alias="num_rows")
    column_count: int = Field(validation_alias="num_columns")
    version: int
    status: str
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DatasetListResponse(BaseModel):
    datasets: list[DatasetResponse]
    total: int


class UploadResponse(BaseModel):
    message: str
    dataset: DatasetResponse


class ErrorResponse(BaseModel):
    detail: str
