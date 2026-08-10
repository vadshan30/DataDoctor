from typing import Any
from pydantic import BaseModel, ConfigDict


class QualityIssue(BaseModel):
    issue_type: str
    severity: str
    column_name: str | None = None
    description: str
    metric_value: Any | None = None


class QualityRecommendation(BaseModel):
    issue_type: str
    recommendation_text: str


class QualitySummary(BaseModel):
    missing_percentage: float
    duplicate_percentage: float
    constant_columns: int
    high_cardinality_columns: int
    outlier_columns: int
    suspicious_columns: int
    potential_identifiers: int


class DataQualityResponse(BaseModel):
    dataset_id: int | None = None
    quality_score: int
    summary: QualitySummary
    issues: list[QualityIssue]
    recommendations: list[QualityRecommendation]

    model_config = ConfigDict(from_attributes=True)
