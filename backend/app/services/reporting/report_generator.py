"""Deterministic report generation service for DataDoctor.

This service generates structured reports for datasets and ML experiments
without using LLMs. All output is deterministic and reproducible based on
actual analysis results stored in the database.
"""

from datetime import datetime
from typing import Any

import os
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dataset import Dataset
from app.models.dataset_profile import DatasetProfile
from app.models.data_quality_report import DataQualityReport
from app.models.cleaned_dataset import CleanedDataset
from app.models.engineered_dataset import EngineeredDataset
from app.models.ml_ready_dataset import MLReadyDataset
from app.models.experiment import Experiment
from app.models.model import TrainedModel
from app.models.report import Report
from app.schemas.report import (
    CleaningSummary,
    DatasetReport,
    DatasetSummary,
    ExperimentReport,
    ExperimentSummary,
    FeatureEngineeringSummary,
    MLPreparationSummary,
    ModelEvaluationSummary,
    ModelSummary,
    QualitySummary,
    ReportFinding,
    ReportRecommendation,
    FeatureImportanceReport,
)
from app.services.data_engine.ingester import read_file
from app.services.ml_engine.explainer import get_feature_importance
from app.services.ml_engine.evaluator import rank_models


class ReportGenerationError(Exception):
    """Raised when report generation fails."""

    pass


class ReportGenerator:
    """Service to generate deterministic, structured reports."""

    def __init__(self, db: Session):
        self.db = db

    def generate_dataset_report(self, dataset_id: int) -> DatasetReport:
        """Generate a complete report for a dataset.

        Aggregates information from:
        - Dataset metadata
        - Dataset profile (if available)
        - Data quality report (if available)
        - Cleaned dataset (if available)
        - Engineered dataset (if available)
        - ML-ready dataset (if available)

        Returns a structured DatasetReport with findings and recommendations.
        """
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ReportGenerationError(f"Dataset {dataset_id} not found")

        # Load existing analysis results from database
        profile = (
            self.db.query(DatasetProfile)
            .filter(DatasetProfile.dataset_id == dataset_id)
            .first()
        )
        quality = (
            self.db.query(DataQualityReport)
            .filter(DataQualityReport.dataset_id == dataset_id)
            .first()
        )
        cleaned = (
            self.db.query(CleanedDataset)
            .filter(CleanedDataset.dataset_id == dataset_id)
            .first()
        )
        engineered = (
            self.db.query(EngineeredDataset)
            .filter(EngineeredDataset.dataset_id == dataset_id)
            .first()
        )
        ml_ready = (
            self.db.query(MLReadyDataset)
            .filter(MLReadyDataset.dataset_id == dataset_id)
            .first()
        )

        experiment = (
            self.db.query(Experiment)
            .filter(Experiment.dataset_id == dataset_id)
            .order_by(Experiment.created_at.desc())
            .first()
        )

        # Build summaries
        dataset_summary = self._build_dataset_summary(dataset, profile)
        quality_summary = self._build_quality_summary(quality)
        cleaning_summary = self._build_cleaning_summary(cleaned)
        feature_engineering_summary = self._build_feature_engineering_summary(engineered)
        ml_preparation_summary = self._build_ml_preparation_summary(ml_ready)
        experiment_summary = (
            self._build_experiment_summary(experiment, ml_ready)
            if experiment
            else None
        )

        # Generate findings and recommendations
        findings = self._generate_dataset_findings(
            dataset_summary, quality_summary, cleaning_summary, feature_engineering_summary
        )
        recommendations = self._generate_dataset_recommendations(
            quality_summary, cleaning_summary, feature_engineering_summary
        )

        return DatasetReport(
            dataset_id=dataset_id,
            dataset_name=dataset.name,
            owner_id=dataset.owner_id,
            status="completed",
            generated_at=datetime.utcnow(),
            dataset_summary=dataset_summary,
            quality_summary=quality_summary,
            cleaning_summary=cleaning_summary,
            feature_engineering_summary=feature_engineering_summary,
            ml_preparation_summary=ml_preparation_summary,
            experiment_summary=experiment_summary,
            findings=findings,
            recommendations=recommendations,
        )

    def generate_experiment_report(
        self, dataset_id: int, experiment_id: int
    ) -> ExperimentReport:
        """Generate a complete report for an ML experiment.

        Aggregates information from:
        - Dataset metadata
        - ML-ready dataset
        - Experiment details
        - Trained models and evaluations
        - Feature importance

        Returns a structured ExperimentReport with findings and recommendations.
        """
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ReportGenerationError(f"Dataset {dataset_id} not found")

        experiment = (
            self.db.query(Experiment)
            .filter(Experiment.id == experiment_id, Experiment.dataset_id == dataset_id)
            .first()
        )
        if not experiment:
            raise ReportGenerationError(
                f"Experiment {experiment_id} not found for dataset {dataset_id}"
            )

        # Load supporting data
        ml_ready = (
            self.db.query(MLReadyDataset)
            .filter(MLReadyDataset.id == experiment.ml_ready_dataset_id)
            .first()
        )

        # Build summaries
        dataset_summary = self._build_dataset_summary(dataset)
        ml_preparation_summary = self._build_ml_preparation_summary(ml_ready)
        experiment_summary = self._build_experiment_summary(experiment, ml_ready)

        # Generate findings and recommendations
        findings = self._generate_experiment_findings(
            dataset_summary, experiment_summary
        )
        recommendations = self._generate_experiment_recommendations(experiment_summary)

        return ExperimentReport(
            dataset_id=dataset_id,
            dataset_name=dataset.name,
            experiment_id=experiment_id,
            experiment_name=experiment.name,
            owner_id=experiment.owner_id,
            status="completed",
            generated_at=datetime.utcnow(),
            dataset_summary=dataset_summary,
            ml_preparation_summary=ml_preparation_summary,
            experiment_summary=experiment_summary,
            findings=findings,
            recommendations=recommendations,
        )

    # ---- Summary builders ----

    def _build_dataset_summary(
        self, dataset: Dataset, profile: DatasetProfile | None = None
    ) -> DatasetSummary:
        """Build a summary of dataset metadata."""
        try:
            file_size_mb = dataset.file_size / (1024 * 1024) if dataset.file_size else 0.0
        except Exception:
            file_size_mb = 0.0

        profile_columns = profile.profile_data.get("columns", []) if profile else []
        return DatasetSummary(
            total_rows=dataset.num_rows,
            total_columns=dataset.num_columns,
            memory_usage_mb=None,  # Could calculate from profile if needed
            file_size_mb=file_size_mb,
            columns=[
                {
                    "name": column.get("column_name", ""),
                    "data_type": column.get("data_type", ""),
                    "pandas_dtype": column.get("pandas_dtype", ""),
                }
                for column in profile_columns
            ],
        )

    def _build_quality_summary(
        self, quality: DataQualityReport | None
    ) -> QualitySummary | None:
        """Build a summary from the data quality report."""
        if not quality:
            return None

        report_data = quality.report_data or {}
        summary = report_data.get("summary", {})
        columns = report_data.get("columns", [])
        missing_values_count = sum(
            int(column.get("null_count", 0)) for column in columns
        )
        return QualitySummary(
            quality_score=quality.quality_score,
            missing_values_count=report_data.get("missing_values_count", missing_values_count),
            missing_values_percentage=report_data.get(
                "missing_values_percentage", summary.get("missing_percentage", 0.0)
            ),
            duplicate_rows=report_data.get("duplicate_rows", report_data.get("duplicate_row_count", 0)),
            duplicate_percentage=report_data.get(
                "duplicate_percentage", summary.get("duplicate_percentage", 0.0)
            ),
            issues=report_data.get("issues", []),
        )

    def _build_cleaning_summary(
        self, cleaned: CleanedDataset | None
    ) -> CleaningSummary | None:
        """Build a summary from cleaning operations."""
        if not cleaned:
            return None

        return CleaningSummary(
            rows_before=cleaned.rows_before,
            rows_after=cleaned.rows_after,
            columns_before=cleaned.columns_before,
            columns_after=cleaned.columns_after,
            missing_values_handled=cleaned.missing_values_handled,
            duplicates_removed=cleaned.duplicates_removed,
            operations=cleaned.cleaning_operations or [],
        )

    def _build_feature_engineering_summary(
        self, engineered: EngineeredDataset | None
    ) -> FeatureEngineeringSummary | None:
        """Build a summary from feature engineering operations."""
        if not engineered:
            return None

        return FeatureEngineeringSummary(
            rows_before=engineered.rows_before,
            rows_after=engineered.rows_after,
            columns_before=engineered.columns_before,
            columns_after=engineered.columns_after,
            features_added=engineered.features_added,
            features_removed=engineered.features_removed,
            feature_names=engineered.feature_names or [],
            operations=engineered.feature_engineering_operations or [],
        )

    def _build_ml_preparation_summary(
        self, ml_ready: MLReadyDataset | None
    ) -> MLPreparationSummary | None:
        """Build a summary from ML-ready dataset preparation."""
        if not ml_ready:
            return None

        return MLPreparationSummary(
            source_dataset_type=ml_ready.source_dataset_type,
            total_rows=ml_ready.rows_after,
            train_rows=ml_ready.train_rows,
            test_rows=ml_ready.test_rows,
            train_test_split=ml_ready.test_size,
            original_features=ml_ready.original_feature_count,
            processed_features=ml_ready.processed_feature_count,
            numeric_columns=len(ml_ready.numeric_columns or []),
            categorical_columns=len(ml_ready.categorical_columns or []),
            feature_names=ml_ready.feature_names or [],
            preprocessing_operations=ml_ready.preprocessing_operations or [],
        )

    def _build_experiment_summary(
        self, experiment: Experiment, ml_ready: MLReadyDataset | None
    ) -> ExperimentSummary:
        """Build a summary of an experiment."""
        # Load all trained models for this experiment
        trained_models = (
            self.db.query(TrainedModel)
            .filter(TrainedModel.experiment_id == experiment.id)
            .all()
        )

        # Build model summaries ranked by experiment's best model logic
        model_summaries = [
            ModelSummary(
                model_id=model.id,
                model_name=model.name,
                algorithm=model.algorithm,
                model_type=model.model_type,
                feature_count=model.feature_count,
                training_rows=model.training_rows,
                validation_rows=model.validation_rows,
                metrics=model.metrics,
            )
            for model in trained_models
        ]
        ranked_models = rank_models(
            [
                {
                    "model_name": model.name,
                    "metrics": model.metrics or {},
                }
                for model in trained_models
                if model.status == "trained"
            ],
            experiment.problem_type,
            experiment.best_metric,
        )
        ranking_order = {model["model_name"]: index for index, model in enumerate(ranked_models)}
        model_summaries.sort(key=lambda model: ranking_order.get(model.model_name, 999))

        # Build evaluation summary
        evaluation = None
        if experiment.best_model_id:
            best_model = (
                self.db.query(TrainedModel)
                .filter(TrainedModel.id == experiment.best_model_id)
                .first()
            )
            if best_model:
                evaluation = ModelEvaluationSummary(
                    total_models_trained=len(trained_models),
                    best_model_id=experiment.best_model_id,
                    best_model_name=best_model.name,
                    best_algorithm=best_model.algorithm,
                    best_metric_name=experiment.best_metric,
                    best_metric_value=experiment.best_score,
                    model_rankings=model_summaries,
                )
        else:
            evaluation = ModelEvaluationSummary(
                total_models_trained=len(trained_models),
                model_rankings=model_summaries,
            )

        # Get feature importance from best model if available
        feature_importance = None
        if experiment.best_model_id:
            best_model = (
                self.db.query(TrainedModel)
                .filter(TrainedModel.id == experiment.best_model_id)
                .first()
            )
            if best_model and best_model.model_path and os.path.exists(best_model.model_path):
                feature_importance = self._get_feature_importance_report(
                    best_model, ml_ready
                )
            elif best_model:
                feature_importance = FeatureImportanceReport(
                    model_name=best_model.name,
                    algorithm=best_model.algorithm,
                    model_type="unknown",
                    is_available=False,
                    message="Feature importance is unavailable because the model artifact is missing.",
                )

        return ExperimentSummary(
            experiment_id=experiment.id,
            experiment_name=experiment.name,
            problem_type=experiment.problem_type,
            target_column=experiment.target_column,
            test_size=experiment.test_size,
            status=experiment.status,
            models_trained=len(trained_models),
            evaluation=evaluation,
            feature_importance=feature_importance,
        )

    # ---- Explainability ----

    def _get_feature_importance_report(
        self, model: TrainedModel, ml_ready: MLReadyDataset | None
    ) -> FeatureImportanceReport | None:
        """Get feature importance for a trained model."""
        try:
            feature_importance = get_feature_importance(
                model.model_path,
                model.algorithm,
                ml_ready.feature_names if ml_ready else None,
            )
            if feature_importance:
                return FeatureImportanceReport(
                    model_name=model.name,
                    algorithm=model.algorithm,
                    model_type=feature_importance.get("type", "unknown"),
                    features=feature_importance.get("features", []),
                    is_available=True,
                )
            else:
                return FeatureImportanceReport(
                    model_name=model.name,
                    algorithm=model.algorithm,
                    model_type="unknown",
                    is_available=False,
                    message=f"Feature importance not available for {model.algorithm}",
                )
        except Exception as e:
            return FeatureImportanceReport(
                model_name=model.name,
                algorithm=model.algorithm,
                model_type="unknown",
                is_available=False,
                message=f"Failed to extract feature importance: {str(e)}",
            )

    # ---- Findings generation ----

    def _generate_dataset_findings(
        self,
        dataset_summary: DatasetSummary,
        quality_summary: QualitySummary | None,
        cleaning_summary: CleaningSummary | None,
        feature_engineering_summary: FeatureEngineeringSummary | None,
    ) -> list[ReportFinding]:
        """Generate key findings for a dataset report."""
        findings: list[ReportFinding] = []

        # Dataset size findings
        findings.append(
            ReportFinding(
                category="dataset",
                title="Dataset Dimensions",
                value=f"{dataset_summary.total_rows} rows × {dataset_summary.total_columns} columns",
                description=f"The dataset contains {dataset_summary.total_rows:,} rows and {dataset_summary.total_columns} columns.",
            )
        )

        # Quality findings
        if quality_summary:
            findings.append(
                ReportFinding(
                    category="quality",
                    title="Overall Data Quality Score",
                    value=quality_summary.quality_score,
                    description=f"Data quality assessment: {quality_summary.quality_score}% with {quality_summary.missing_values_count} missing values.",
                )
            )
            if quality_summary.missing_values_percentage > 0:
                findings.append(
                    ReportFinding(
                        category="data_issues",
                        title="Missing Values",
                        value=f"{quality_summary.missing_values_percentage:.1f}%",
                        description=f"Missing values detected in {quality_summary.missing_values_count} cells ({quality_summary.missing_values_percentage:.1f}% of data).",
                    )
                )
            if quality_summary.duplicate_rows > 0:
                findings.append(
                    ReportFinding(
                        category="data_issues",
                        title="Duplicate Rows",
                        value=quality_summary.duplicate_rows,
                        description=f"Found {quality_summary.duplicate_rows} duplicate rows ({quality_summary.duplicate_percentage:.1f}% of data).",
                    )
                )

        # Cleaning findings
        if cleaning_summary and cleaning_summary.rows_before != cleaning_summary.rows_after:
            rows_removed = cleaning_summary.rows_before - cleaning_summary.rows_after
            findings.append(
                ReportFinding(
                    category="dataset",
                    title="Data Cleaning Impact",
                    value=rows_removed,
                    description=f"Cleaning operations removed {rows_removed} rows and handled {cleaning_summary.missing_values_handled} missing values.",
                )
            )

        # Feature engineering findings
        if feature_engineering_summary:
            net_features_change = (
                feature_engineering_summary.features_added
                - feature_engineering_summary.features_removed
            )
            findings.append(
                ReportFinding(
                    category="features",
                    title="Feature Engineering Summary",
                    value=f"{feature_engineering_summary.columns_after} features",
                    description=f"Feature engineering added {feature_engineering_summary.features_added} features and removed {feature_engineering_summary.features_removed} features. Final feature count: {feature_engineering_summary.columns_after}.",
                )
            )

        return findings

    def _generate_experiment_findings(
        self,
        dataset_summary: DatasetSummary,
        experiment_summary: ExperimentSummary,
    ) -> list[ReportFinding]:
        """Generate key findings for an experiment report."""
        findings: list[ReportFinding] = []

        # Dataset findings
        findings.append(
            ReportFinding(
                category="dataset",
                title="Dataset Size",
                value=f"{dataset_summary.total_rows:,} rows",
                description=f"Experiment trained on {dataset_summary.total_rows:,} rows with {dataset_summary.total_columns} original columns.",
            )
        )

        # Model findings
        findings.append(
            ReportFinding(
                category="model",
                title="Models Trained",
                value=experiment_summary.models_trained,
                description=f"Total of {experiment_summary.models_trained} models trained during this experiment.",
            )
        )

        # Best model findings
        if (
            experiment_summary.evaluation
            and experiment_summary.evaluation.best_model_name
        ):
            findings.append(
                ReportFinding(
                    category="model",
                    title="Best Performing Model",
                    value=experiment_summary.evaluation.best_model_name,
                    description=f"Best model: {experiment_summary.evaluation.best_model_name} ({experiment_summary.evaluation.best_algorithm}) with {experiment_summary.evaluation.best_metric_name}={experiment_summary.evaluation.best_metric_value:.4f}",
                )
            )

        # Feature count finding
        if experiment_summary.evaluation and experiment_summary.evaluation.model_rankings:
            best_model = experiment_summary.evaluation.model_rankings[0]
            findings.append(
                ReportFinding(
                    category="features",
                    title="Feature Count",
                    value=best_model.feature_count,
                    description=f"Best model trained with {best_model.feature_count} features.",
                )
            )

        return findings

    # ---- Recommendations generation ----

    def _generate_dataset_recommendations(
        self,
        quality_summary: QualitySummary | None,
        cleaning_summary: CleaningSummary | None,
        feature_engineering_summary: FeatureEngineeringSummary | None,
    ) -> list[ReportRecommendation]:
        """Generate recommendations for a dataset report."""
        recommendations: list[ReportRecommendation] = []

        # Quality-based recommendations
        if quality_summary:
            if quality_summary.quality_score < 70:
                recommendations.append(
                    ReportRecommendation(
                        priority="high",
                        category="data_quality",
                        title="Low Data Quality Score",
                        description=f"Data quality score is {quality_summary.quality_score}%. This may impact model performance.",
                        action="Review and address data quality issues. Consider additional cleaning, imputation, or outlier handling.",
                    )
                )
            if quality_summary.missing_values_percentage > 30:
                recommendations.append(
                    ReportRecommendation(
                        priority="high",
                        category="data_quality",
                        title="High Missing Value Rate",
                        description=f"{quality_summary.missing_values_percentage:.1f}% of values are missing.",
                        action="Consider advanced imputation techniques, removing highly sparse columns, or feature engineering to handle missing values.",
                    )
                )
            if quality_summary.duplicate_percentage > 5:
                recommendations.append(
                    ReportRecommendation(
                        priority="medium",
                        category="data_quality",
                        title="Duplicate Rows Detected",
                        description=f"{quality_summary.duplicate_percentage:.1f}% of rows are duplicates.",
                        action="Review and remove or consolidate duplicate records based on business logic.",
                    )
                )

        # Cleaning-based recommendations
        if cleaning_summary and cleaning_summary.rows_before > 0:
            removal_rate = (
                (cleaning_summary.rows_before - cleaning_summary.rows_after)
                / cleaning_summary.rows_before
                * 100
            )
            if removal_rate > 20:
                recommendations.append(
                    ReportRecommendation(
                        priority="medium",
                        category="preprocessing",
                        title="High Data Removal Rate",
                        description=f"Cleaning removed {removal_rate:.1f}% of rows. This may result in insufficient data for modeling.",
                        action="Review cleaning operations. Consider more conservative imputation strategies or selective filtering.",
                    )
                )

        # Feature-based recommendations
        if feature_engineering_summary and feature_engineering_summary.columns_after > 100:
            recommendations.append(
                ReportRecommendation(
                    priority="medium",
                    category="features",
                    title="High Feature Dimensionality",
                    description=f"Dataset has {feature_engineering_summary.columns_after} features. This may cause overfitting.",
                    action="Consider feature selection, dimensionality reduction (PCA), or regularization techniques.",
                )
            )

        return recommendations

    def _generate_experiment_recommendations(
        self, experiment_summary: ExperimentSummary
    ) -> list[ReportRecommendation]:
        """Generate recommendations for an experiment report."""
        recommendations: list[ReportRecommendation] = []

        if not experiment_summary.evaluation:
            return recommendations

        best_score = experiment_summary.evaluation.best_metric_value
        best_metric = experiment_summary.evaluation.best_metric_name

        # Performance-based recommendations
        if best_metric == "f1" and best_score is not None and best_score < 0.7:
            recommendations.append(
                ReportRecommendation(
                    priority="high",
                    category="model",
                    title="Poor Model Performance",
                    description=f"Best model F1 score is {best_score:.4f}. Performance may be insufficient for production.",
                    action="Consider more feature engineering, different algorithms, hyperparameter tuning, or collecting more data.",
                )
            )
        elif best_metric == "r2" and best_score is not None and best_score < 0.6:
            recommendations.append(
                ReportRecommendation(
                    priority="high",
                    category="model",
                    title="Poor Model Performance (R²)",
                    description=f"Best model R² score is {best_score:.4f}. Model explains less than 60% of variance.",
                    action="Improve feature engineering, try different algorithms, or investigate data quality issues.",
                )
            )

        # Model diversity recommendations
        if experiment_summary.models_trained >= 2:
            models_by_algo = {}
            for model in experiment_summary.evaluation.model_rankings:
                models_by_algo[model.algorithm] = models_by_algo.get(model.algorithm, 0) + 1

            if len(models_by_algo) == 1:
                recommendations.append(
                    ReportRecommendation(
                        priority="low",
                        category="model",
                        title="Limited Algorithm Diversity",
                        description=f"All {experiment_summary.models_trained} models use the same algorithm.",
                        action="Consider training with different algorithms to find the best approach for your problem.",
                    )
                )

        return recommendations
