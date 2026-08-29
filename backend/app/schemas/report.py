from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---- Feature Importance Schema ----


class FeatureImportance(BaseModel):
    """Represents the importance of a single feature in a model."""

    feature_name: str
    importance_value: float
    normalized_importance: float  # 0.0 to 1.0
    rank: int  # 1-based ranking


class FeatureImportanceReport(BaseModel):
    """Report on feature importance for a trained model."""

    model_name: str
    algorithm: str
    model_type: str  # "tree" or "linear"
    features: list[FeatureImportance] = Field(default_factory=list)
    is_available: bool = True
    message: str | None = None  # Message if feature importance is unavailable


# ---- Findings and Recommendations ----


class ReportFinding(BaseModel):
    """A key finding from the dataset or ML analysis."""

    category: str  # "dataset", "quality", "features", "model", "data_issues"
    title: str
    value: str | int | float
    description: str


class ReportRecommendation(BaseModel):
    """A recommendation based on the analysis."""

    priority: str  # "high", "medium", "low"
    category: str  # "data_quality", "features", "model", "preprocessing"
    title: str
    description: str
    action: str  # Suggested action to take


# ---- Summary Schemas ----


class DatasetSummary(BaseModel):
    """Overview of the dataset."""

    total_rows: int
    total_columns: int
    memory_usage_mb: float | None = None
    file_size_mb: float
    columns: list[dict[str, str]] = Field(default_factory=list)


class QualitySummary(BaseModel):
    """Summary of data quality analysis."""

    quality_score: int  # 0-100
    missing_values_count: int
    missing_values_percentage: float
    duplicate_rows: int
    duplicate_percentage: float
    issues: list[dict[str, Any]] = Field(default_factory=list)


class CleaningSummary(BaseModel):
    """Summary of data cleaning operations."""

    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    missing_values_handled: int
    duplicates_removed: int
    operations: list[dict[str, Any]] = Field(default_factory=list)


class FeatureEngineeringSummary(BaseModel):
    """Summary of feature engineering operations."""

    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    features_added: int
    features_removed: int
    feature_names: list[str] = Field(default_factory=list)
    operations: list[dict[str, Any]] = Field(default_factory=list)


class MLPreparationSummary(BaseModel):
    """Summary of ML dataset preparation."""

    source_dataset_type: str  # "original", "cleaned", or "engineered"
    total_rows: int
    train_rows: int
    test_rows: int
    train_test_split: float
    original_features: int
    processed_features: int
    numeric_columns: int
    categorical_columns: int
    feature_names: list[str] = Field(default_factory=list)
    preprocessing_operations: list[dict[str, Any]] = Field(default_factory=list)


class ModelSummary(BaseModel):
    """Summary of a trained model."""

    model_id: int
    model_name: str
    algorithm: str
    model_type: str
    feature_count: int
    training_rows: int
    validation_rows: int
    metrics: dict[str, Any] | None = None


class ModelEvaluationSummary(BaseModel):
    """Summary of model evaluation."""

    total_models_trained: int
    best_model_id: int | None = None
    best_model_name: str | None = None
    best_algorithm: str | None = None
    best_metric_name: str | None = None
    best_metric_value: float | None = None
    model_rankings: list[ModelSummary] = Field(default_factory=list)


class ExperimentSummary(BaseModel):
    """Summary of an ML experiment."""

    experiment_id: int | None = None
    experiment_name: str | None = None
    problem_type: str
    target_column: str | None = None
    test_size: float
    status: str
    models_trained: int
    evaluation: ModelEvaluationSummary | None = None
    feature_importance: FeatureImportanceReport | None = None


# ---- Main Report Schemas ----


class DatasetReport(BaseModel):
    """Complete report for a dataset."""

    report_id: int | None = None
    report_type: str = "dataset"
    dataset_id: int
    dataset_name: str
    owner_id: int
    status: str = "completed"
    generated_at: datetime
    
    dataset_summary: DatasetSummary | None = None
    quality_summary: QualitySummary | None = None
    cleaning_summary: CleaningSummary | None = None
    feature_engineering_summary: FeatureEngineeringSummary | None = None
    ml_preparation_summary: MLPreparationSummary | None = None
    experiment_summary: ExperimentSummary | None = None
    
    findings: list[ReportFinding] = Field(default_factory=list)
    recommendations: list[ReportRecommendation] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)


class ExperimentReport(BaseModel):
    """Complete report for an ML experiment."""

    report_id: int | None = None
    report_type: str = "experiment"
    dataset_id: int
    dataset_name: str
    experiment_id: int
    experiment_name: str
    owner_id: int
    status: str = "completed"
    generated_at: datetime
    
    dataset_summary: DatasetSummary | None = None
    ml_preparation_summary: MLPreparationSummary | None = None
    experiment_summary: ExperimentSummary | None = None
    
    findings: list[ReportFinding] = Field(default_factory=list)
    recommendations: list[ReportRecommendation] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)


# ---- API Response Schemas ----


class ReportResponse(BaseModel):
    """API response for a single report."""

    report_id: int = Field(validation_alias="id")
    name: str | None = None
    report_type: str
    dataset_id: int
    dataset_name: str | None = None
    experiment_id: int | None = None
    experiment_name: str | None = None
    owner_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    report_data: DatasetReport | ExperimentReport | dict[str, Any] | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ReportListResponse(BaseModel):
    """API response for a list of reports."""

    reports: list[ReportResponse] = Field(default_factory=list)
    total: int


class ReportGenerationRequest(BaseModel):
    """Request to generate a report."""

    regenerate: bool = False  # Force regeneration even if cached
