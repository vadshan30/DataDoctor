import os
import uuid

import pandas as pd

from app.services.data_engine.ingester import read_file
from app.utils.helpers import generate_unique_filename


def _generate_cleaned_filename(original_file_path: str) -> str:
    base = os.path.basename(original_file_path)
    name, ext = os.path.splitext(base)
    return f"{name}_cleaned_{uuid.uuid4().hex}{ext}"


def _save_cleaned_file(df: pd.DataFrame, file_path: str) -> None:
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext == ".csv":
        df.to_csv(file_path, index=False)
    elif ext == ".xlsx":
        df.to_excel(file_path, index=False, engine="openpyxl")
    elif ext == ".xls":
        df.to_excel(file_path, index=False, engine="xlwt")
    else:
        df.to_csv(file_path, index=False)


def _handle_empty_strings(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    operations = []
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            str_series = df[col].astype(str)
            mask = str_series.str.strip() == ""
            mask = mask & df[col].notna()
            count = int(mask.sum())
            if count > 0:
                df.loc[mask, col] = pd.NA
                operations.append({
                    "operation": "empty_string_as_missing",
                    "column": str(col),
                    "affected_rows": count,
                    "strategy": "treat_as_missing",
                    "replacement_value": None,
                    "detail": f"Converted {count} empty/whitespace-only strings to NA in column '{col}'.",
                })
    return df, operations


def _impute_numeric(series: pd.Series) -> tuple[pd.Series, dict | None]:
    missing_mask = series.isna()
    count = int(missing_mask.sum())
    if count == 0:
        return series, None

    non_null = series.dropna()
    if len(non_null) == 0:
        return series, {
            "operation": "missing_values_unresolved",
            "column": str(series.name),
            "affected_rows": count,
            "strategy": "no_usable_values",
            "replacement_value": None,
            "detail": f"Column '{series.name}' has no usable values; cannot impute.",
        }

    median_val = non_null.median()
    series = series.fillna(median_val)
    return series, {
        "operation": "median_imputation",
        "column": str(series.name),
        "affected_rows": count,
        "strategy": "median",
        "replacement_value": float(median_val) if pd.notna(median_val) else None,
        "detail": f"Imputed {count} missing values with median={median_val} in column '{series.name}'.",
    }


def _impute_categorical(series: pd.Series) -> tuple[pd.Series, dict | None]:
    missing_mask = series.isna()
    count = int(missing_mask.sum())
    if count == 0:
        return series, None

    non_null = series.dropna()
    if len(non_null) == 0:
        return series, {
            "operation": "missing_values_unresolved",
            "column": str(series.name),
            "affected_rows": count,
            "strategy": "no_usable_values",
            "replacement_value": None,
            "detail": f"Column '{series.name}' has no usable values; cannot impute.",
        }

    mode_result = non_null.mode()
    if len(mode_result) == 0:
        return series, {
            "operation": "missing_values_unresolved",
            "column": str(series.name),
            "affected_rows": count,
            "strategy": "no_mode_found",
            "replacement_value": None,
            "detail": f"Column '{series.name}' has no mode; cannot impute.",
        }

    mode_val = mode_result.iloc[0]
    series = series.fillna(mode_val)
    return series, {
        "operation": "mode_imputation",
        "column": str(series.name),
        "affected_rows": count,
        "strategy": "mode",
        "replacement_value": str(mode_val) if not isinstance(mode_val, (int, float, bool)) else mode_val,
        "detail": f"Imputed {count} missing values with mode='{mode_val}' in column '{series.name}'.",
    }


def _handle_missing_values(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict], int]:
    operations = []
    total_imputed = 0

    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            series, op = _impute_numeric(series)
        else:
            series, op = _impute_categorical(series)

        if op is not None:
            operations.append(op)
            if op["operation"] in ("median_imputation", "mode_imputation"):
                total_imputed += op["affected_rows"]
        df[col] = series

    return df, operations, total_imputed


def _remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, dict | None]:
    duplicate_count = int(df.duplicated().sum())
    if duplicate_count == 0:
        return df, None
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    return df, {
        "operation": "duplicate_removal",
        "column": None,
        "affected_rows": duplicate_count,
        "strategy": "keep_first",
        "replacement_value": None,
        "detail": f"Removed {duplicate_count} duplicate rows, keeping first occurrence.",
    }


def clean_dataset(original_file_path: str, upload_dir: str) -> dict:
    if not os.path.exists(original_file_path):
        raise FileNotFoundError(f"Original file not found: {original_file_path}")

    df = read_file(original_file_path)
    rows_before = len(df)
    columns_before = len(df.columns)

    all_operations = []

    df, empty_ops = _handle_empty_strings(df)
    all_operations.extend(empty_ops)

    df, missing_ops, total_imputed = _handle_missing_values(df)
    all_operations.extend(missing_ops)

    df, dup_op = _remove_duplicates(df)
    if dup_op is not None:
        all_operations.append(dup_op)

    rows_after = len(df)
    columns_after = len(df.columns)
    duplicates_removed = dup_op["affected_rows"] if dup_op else 0

    cleaned_filename = _generate_cleaned_filename(original_file_path)
    cleaned_file_path = os.path.join(upload_dir, cleaned_filename)
    _save_cleaned_file(df, cleaned_file_path)

    return {
        "original_file_path": original_file_path,
        "cleaned_file_path": cleaned_file_path,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "columns_before": columns_before,
        "columns_after": columns_after,
        "missing_values_handled": total_imputed,
        "duplicates_removed": duplicates_removed,
        "cleaning_status": "completed",
        "cleaning_operations": all_operations,
    }
