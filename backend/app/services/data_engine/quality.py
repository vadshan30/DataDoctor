import pandas as pd
import numpy as np

from app.schemas.quality import (
    DataQualityResponse,
    QualityIssue,
    QualityRecommendation,
    QualitySummary
)


def analyze_quality(df: pd.DataFrame, dataset_id: int | None = None) -> DataQualityResponse:
    row_count = len(df)
    if row_count == 0:
        return DataQualityResponse(
            dataset_id=dataset_id,
            quality_score=0,
            summary=QualitySummary(
                missing_percentage=100.0,
                duplicate_percentage=0.0,
                constant_columns=0,
                high_cardinality_columns=0,
                outlier_columns=0,
                suspicious_columns=0,
                potential_identifiers=0
            ),
            issues=[QualityIssue(issue_type="empty_dataset", severity="high", description="Dataset is empty")],
            recommendations=[QualityRecommendation(issue_type="empty_dataset", recommendation_text="Upload a valid dataset with data.")]
        )
        
    issues = []
    
    # Missing values
    total_missing = 0
    total_cells = row_count * len(df.columns)
    
    # Duplicates
    duplicate_count = int(df.duplicated().sum())
    duplicate_percentage = (duplicate_count / row_count) * 100
    if duplicate_percentage > 0:
        severity = "high" if duplicate_percentage > 20 else "medium" if duplicate_percentage > 5 else "low"
        issues.append(QualityIssue(
            issue_type="duplicate_rows",
            severity=severity,
            description=f"Dataset has {duplicate_count} duplicate rows ({duplicate_percentage:.2f}%).",
            metric_value=duplicate_percentage
        ))

    constant_cols = 0
    high_cardinality_cols = 0
    outlier_cols = 0
    suspicious_cols = 0
    potential_identifiers = 0

    for col in df.columns:
        series = df[col]
        missing_count = int(series.isnull().sum())
        total_missing += missing_count
        missing_pct = (missing_count / row_count) * 100
        
        if missing_pct > 0:
            sev = "high" if missing_pct > 20 else "medium" if missing_pct > 5 else "low"
            issues.append(QualityIssue(
                issue_type="missing_values",
                severity=sev,
                column_name=str(col),
                description=f"Column has {missing_count} missing values ({missing_pct:.2f}%).",
                metric_value=missing_pct
            ))
            
        non_null_series = series.dropna()
        if len(non_null_series) == 0:
            continue
            
        unique_count = int(non_null_series.nunique())
        
        # Constant and Near Constant
        if unique_count == 1:
            constant_cols += 1
            issues.append(QualityIssue(
                issue_type="constant_column",
                severity="high",
                column_name=str(col),
                description="Column has only 1 unique value.",
                metric_value=1
            ))
        elif unique_count > 1:
            top_val_count = int(non_null_series.value_counts().iloc[0])
            if (top_val_count / len(non_null_series)) > 0.99:
                constant_cols += 1
                issues.append(QualityIssue(
                    issue_type="near_constant_column",
                    severity="medium",
                    column_name=str(col),
                    description="Column is near-constant (>99% same value).",
                    metric_value=top_val_count / len(non_null_series)
                ))
                
        # Numeric checks
        if pd.api.types.is_numeric_dtype(non_null_series) and not pd.api.types.is_bool_dtype(non_null_series):
            q1 = non_null_series.quantile(0.25)
            q3 = non_null_series.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = non_null_series[(non_null_series < lower_bound) | (non_null_series > upper_bound)]
                outlier_count = int(outliers.count())
                if outlier_count > 0:
                    outlier_cols += 1
                    outlier_pct = (outlier_count / row_count) * 100
                    sev = "high" if outlier_pct > 10 else "medium" if outlier_pct > 5 else "low"
                    issues.append(QualityIssue(
                        issue_type="numeric_outliers",
                        severity=sev,
                        column_name=str(col),
                        description=f"Column has {outlier_count} IQR outliers ({outlier_pct:.2f}%).",
                        metric_value=outlier_pct
                    ))
            
            # Suspicious values
            col_lower = str(col).lower()
            if any(k in col_lower for k in ['qty', 'quantity', 'amount', 'count', 'price', 'balance']):
                negatives = int((non_null_series < 0).sum())
                if negatives > 0:
                    suspicious_cols += 1
                    issues.append(QualityIssue(
                        issue_type="suspicious_values",
                        severity="high",
                        column_name=str(col),
                        description=f"Found {negatives} negative values in a likely quantity column.",
                        metric_value=negatives
                    ))
        
        # Categorical / String Checks
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            if unique_count > 10 and (unique_count / len(non_null_series)) > 0.5:
                high_cardinality_cols += 1
                issues.append(QualityIssue(
                    issue_type="high_cardinality",
                    severity="low",
                    column_name=str(col),
                    description=f"Categorical column has very high cardinality ({unique_count} unique).",
                    metric_value=unique_count
                ))
                
            str_series = non_null_series.astype(str).str.strip()
            empty_strings = int((str_series == "").sum())
            if empty_strings > 0:
                suspicious_cols += 1
                issues.append(QualityIssue(
                    issue_type="suspicious_values",
                    severity="medium",
                    column_name=str(col),
                    description=f"Found {empty_strings} empty or whitespace-only strings.",
                    metric_value=empty_strings
                ))

        # Potential identifier detection — applies to ALL dtypes for name signals, but
        # uniqueness-based detection only applies to string/object columns since numeric columns
        # commonly have all-unique values without being identifiers (e.g. measurements, prices).
        col_lower = str(col).lower()
        is_named_identifier = 'id' in col_lower or 'uuid' in col_lower
        is_string_col = pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)
        is_fully_unique_string = is_string_col and (unique_count == len(non_null_series) and unique_count > 1)
        if is_named_identifier or is_fully_unique_string:
            potential_identifiers += 1
            issues.append(QualityIssue(
                issue_type="potential_identifier",
                severity="low",
                column_name=str(col),
                description="Column appears to be an identifier (name contains 'id'/'uuid' or is a fully unique string column).",
                metric_value=unique_count
            ))

    # Scoring
    score = 100
    for issue in issues:
        if issue.severity == "high":
            score -= 5
        elif issue.severity == "medium":
            score -= 2
        elif issue.severity == "low":
            score -= 1
            
    score = max(0, min(100, score))
    
    # Recommendations
    recommendations_map = {
        "missing_values": "Consider imputing or removing missing values depending on the column's role and missingness rate.",
        "duplicate_rows": "Review duplicate records and remove them if they represent repeated observations.",
        "constant_column": "Consider removing this column because it contains no useful variation.",
        "near_constant_column": "Consider whether the slight variation in this column is meaningful or if it can be dropped.",
        "numeric_outliers": "Review extreme values and determine whether they are legitimate observations or potential data-entry errors.",
        "high_cardinality": "Consider grouping infrequent categories or applying target encoding for predictive modeling.",
        "suspicious_values": "Investigate anomalous values (e.g. negative prices, empty strings) as they likely indicate data entry errors.",
        "potential_identifier": "Review whether this column should be excluded from model training because it may uniquely identify records."
    }
    
    recs_added = set()
    recommendations = []
    for issue in issues:
        if issue.issue_type not in recs_added and issue.issue_type in recommendations_map:
            recommendations.append(QualityRecommendation(
                issue_type=issue.issue_type,
                recommendation_text=recommendations_map[issue.issue_type]
            ))
            recs_added.add(issue.issue_type)
            
    summary = QualitySummary(
        missing_percentage=(total_missing / total_cells) * 100 if total_cells > 0 else 0.0,
        duplicate_percentage=duplicate_percentage,
        constant_columns=constant_cols,
        high_cardinality_columns=high_cardinality_cols,
        outlier_columns=outlier_cols,
        suspicious_columns=suspicious_cols,
        potential_identifiers=potential_identifiers
    )

    return DataQualityResponse(
        dataset_id=dataset_id,
        quality_score=score,
        summary=summary,
        issues=issues,
        recommendations=recommendations
    )
