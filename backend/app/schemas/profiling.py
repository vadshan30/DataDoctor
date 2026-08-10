from typing import Any
from pydantic import BaseModel, ConfigDict


class OutlierProfile(BaseModel):
    count: int
    percentage: float
    lower_bound: float
    upper_bound: float


class NumericProfile(BaseModel):
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    standard_deviation: float | None = None
    variance: float | None = None
    q1: float | None = None
    q3: float | None = None
    iqr: float | None = None
    outliers: OutlierProfile | None = None


class CategoricalProfile(BaseModel):
    top_values: list[Any]
    top_value_counts: list[int]
    top_value_percentage: list[float]


class DatetimeProfile(BaseModel):
    min_date: str | None = None
    max_date: str | None = None


class ColumnProfile(BaseModel):
    column_name: str
    data_type: str
    pandas_dtype: str
    null_count: int
    null_percentage: float
    non_null_count: int
    unique_count: int
    unique_percentage: float
    
    numeric_stats: NumericProfile | None = None
    categorical_stats: CategoricalProfile | None = None
    datetime_stats: DatetimeProfile | None = None


class DatasetProfileResponse(BaseModel):
    row_count: int
    column_count: int
    duplicate_row_count: int
    duplicate_row_percentage: float
    memory_usage: int
    
    numerical_column_count: int
    categorical_column_count: int
    datetime_column_count: int
    boolean_column_count: int
    
    columns: list[ColumnProfile]

    model_config = ConfigDict(from_attributes=True)
