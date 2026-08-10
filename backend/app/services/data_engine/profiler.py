import pandas as pd
import numpy as np
from typing import Any

from app.schemas.profiling import (
    DatasetProfileResponse,
    ColumnProfile,
    NumericProfile,
    OutlierProfile,
    CategoricalProfile,
    DatetimeProfile,
)


def _safe_float(val: Any) -> float | None:
    if pd.isna(val) or np.isinf(val):
        return None
    return float(val)


def generate_profile(df: pd.DataFrame) -> DatasetProfileResponse:
    row_count = len(df)
    column_count = len(df.columns)
    
    # Dataset level stats
    duplicate_row_count = int(df.duplicated().sum())
    duplicate_row_percentage = (duplicate_row_count / row_count) * 100 if row_count > 0 else 0.0
    memory_usage = int(df.memory_usage(deep=True).sum())
    
    numerical_cols = 0
    categorical_cols = 0
    datetime_cols = 0
    boolean_cols = 0
    
    columns = []
    
    for col in df.columns:
        series = df[col]
        pandas_dtype = str(series.dtype)
        
        null_count = int(series.isnull().sum())
        non_null_count = row_count - null_count
        null_percentage = (null_count / row_count) * 100 if row_count > 0 else 0.0
        
        unique_count = int(series.nunique(dropna=True))
        unique_percentage = (unique_count / row_count) * 100 if row_count > 0 else 0.0
        
        numeric_stats = None
        categorical_stats = None
        datetime_stats = None
        
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            numerical_cols += 1
            data_type = "numerical"
            
            # Numeric stats
            q1 = _safe_float(series.quantile(0.25))
            q3 = _safe_float(series.quantile(0.75))
            iqr = _safe_float(q3 - q1) if q1 is not None and q3 is not None else None
            
            outlier_profile = None
            if q1 is not None and q3 is not None and iqr is not None:
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = series[(series < lower_bound) | (series > upper_bound)]
                outlier_count = int(outliers.count())
                outlier_percentage = (outlier_count / row_count) * 100 if row_count > 0 else 0.0
                outlier_profile = OutlierProfile(
                    count=outlier_count,
                    percentage=outlier_percentage,
                    lower_bound=lower_bound,
                    upper_bound=upper_bound
                )
            
            numeric_stats = NumericProfile(
                min=_safe_float(series.min()),
                max=_safe_float(series.max()),
                mean=_safe_float(series.mean()),
                median=_safe_float(series.median()),
                standard_deviation=_safe_float(series.std()),
                variance=_safe_float(series.var()),
                q1=q1,
                q3=q3,
                iqr=iqr,
                outliers=outlier_profile
            )
            
        elif pd.api.types.is_datetime64_any_dtype(series):
            datetime_cols += 1
            data_type = "datetime"
            min_date = series.min()
            max_date = series.max()
            datetime_stats = DatetimeProfile(
                min_date=str(min_date) if not pd.isna(min_date) else None,
                max_date=str(max_date) if not pd.isna(max_date) else None
            )
            
        elif pd.api.types.is_bool_dtype(series):
            boolean_cols += 1
            data_type = "boolean"
            
        else:
            categorical_cols += 1
            data_type = "categorical"
            
            # Categorical stats
            val_counts = series.value_counts(dropna=True).head(10)
            top_values = val_counts.index.tolist()
            top_value_counts = val_counts.values.tolist()
            top_value_percentage = [(c / row_count) * 100 for c in top_value_counts] if row_count > 0 else []
            
            # Convert non-serializable objects (like pd.Timestamp) in top_values to str if needed
            top_values = [str(v) if not isinstance(v, (int, float, str, bool)) else v for v in top_values]
            
            categorical_stats = CategoricalProfile(
                top_values=top_values,
                top_value_counts=top_value_counts,
                top_value_percentage=top_value_percentage
            )
            
        columns.append(ColumnProfile(
            column_name=str(col),
            data_type=data_type,
            pandas_dtype=pandas_dtype,
            null_count=null_count,
            null_percentage=null_percentage,
            non_null_count=non_null_count,
            unique_count=unique_count,
            unique_percentage=unique_percentage,
            numeric_stats=numeric_stats,
            categorical_stats=categorical_stats,
            datetime_stats=datetime_stats
        ))
        
    return DatasetProfileResponse(
        row_count=row_count,
        column_count=column_count,
        duplicate_row_count=duplicate_row_count,
        duplicate_row_percentage=duplicate_row_percentage,
        memory_usage=memory_usage,
        numerical_column_count=numerical_cols,
        categorical_column_count=categorical_cols,
        datetime_column_count=datetime_cols,
        boolean_column_count=boolean_cols,
        columns=columns
    )
