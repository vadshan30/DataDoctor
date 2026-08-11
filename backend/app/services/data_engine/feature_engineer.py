import os
import uuid

import numpy as np
import pandas as pd

from app.services.data_engine.ingester import read_file


def _generate_engineered_filename(source_file_path: str) -> str:
    base = os.path.basename(source_file_path)
    name, ext = os.path.splitext(base)
    return f"{name}_engineered_{uuid.uuid4().hex}{ext}"


def _save_engineered_file(df: pd.DataFrame, file_path: str) -> None:
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


def _is_object_or_string(series: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)


def _is_numeric_column(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def _is_datetime_column(series: pd.Series, threshold: float = 0.8) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if _is_object_or_string(series):
        non_null = series.dropna()
        if len(non_null) == 0:
            return False
        parsed = pd.to_datetime(non_null, errors="coerce")
        parse_rate = parsed.notna().sum() / len(non_null)
        return parse_rate >= threshold
    return False


def _is_categorical(series: pd.Series, ratio_threshold: float = 0.5) -> bool:
    if _is_object_or_string(series):
        non_null = series.dropna()
        if len(non_null) == 0:
            return False
        unique_count = non_null.nunique()
        if unique_count <= 1:
            return True
        ratio = unique_count / len(non_null)
        return ratio <= ratio_threshold
    return False


def _classify_columns(df: pd.DataFrame, original_columns: list[str]) -> tuple[set, set, set, set]:
    datetime_cols: set[str] = set()
    numeric_cols: set[str] = set()
    text_cols: set[str] = set()
    categorical_cols: set[str] = set()

    for col in original_columns:
        if _is_datetime_column(df[col]):
            datetime_cols.add(col)
        elif _is_numeric_column(df[col]):
            numeric_cols.add(col)
        elif _is_object_or_string(df[col]):
            if _is_categorical(df[col]):
                categorical_cols.add(col)
            else:
                text_cols.add(col)

    return datetime_cols, numeric_cols, text_cols, categorical_cols


def _extract_datetime_features(
    df: pd.DataFrame, datetime_cols: set[str]
) -> tuple[pd.DataFrame, list[dict], list[str]]:
    operations: list[dict] = []
    new_features: list[str] = []

    for col in datetime_cols:
        dt_series = pd.to_datetime(df[col], errors="coerce")

        new_cols = [
            f"{col}_year",
            f"{col}_month",
            f"{col}_day",
            f"{col}_day_of_week",
            f"{col}_quarter",
            f"{col}_is_weekend",
        ]

        df[f"{col}_year"] = dt_series.dt.year
        df[f"{col}_month"] = dt_series.dt.month
        df[f"{col}_day"] = dt_series.dt.day
        df[f"{col}_day_of_week"] = dt_series.dt.dayofweek
        df[f"{col}_quarter"] = dt_series.dt.quarter
        df[f"{col}_is_weekend"] = (dt_series.dt.dayofweek >= 5).astype(int)

        min_date = dt_series.min()
        if pd.notna(min_date):
            df[f"{col}_days_since_reference"] = (dt_series - min_date).dt.days
            new_cols.append(f"{col}_days_since_reference")

        new_features.extend(new_cols)
        operations.append({
            "operation": "date_extraction",
            "column": str(col),
            "new_features": new_cols,
            "strategy": "component_extraction",
            "detail": f"Extracted {len(new_cols)} datetime features from '{col}'.",
        })

    return df, operations, new_features


def _extract_text_features(
    df: pd.DataFrame, text_cols: set[str]
) -> tuple[pd.DataFrame, list[dict], list[str]]:
    operations: list[dict] = []
    new_features: list[str] = []

    for col in text_cols:
        str_series = df[col].fillna("").astype(str)

        new_cols = [
            f"{col}_word_count",
            f"{col}_char_count",
            f"{col}_avg_word_length",
            f"{col}_uppercase_count",
            f"{col}_lowercase_count",
            f"{col}_punctuation_count",
        ]

        words = str_series.str.split()
        df[f"{col}_word_count"] = words.str.len().fillna(0).astype(int)
        df[f"{col}_char_count"] = str_series.str.len()
        df[f"{col}_avg_word_length"] = words.apply(
            lambda w: float(np.mean([len(x) for x in w])) if len(w) > 0 else 0.0
        )
        df[f"{col}_uppercase_count"] = str_series.str.count(r"[A-Z]")
        df[f"{col}_lowercase_count"] = str_series.str.count(r"[a-z]")
        df[f"{col}_punctuation_count"] = str_series.str.count(r"[^\w\s]")

        new_features.extend(new_cols)
        operations.append({
            "operation": "text_features",
            "column": str(col),
            "new_features": new_cols,
            "strategy": "statistical_extraction",
            "detail": f"Extracted {len(new_cols)} text features from '{col}'.",
        })

    return df, operations, new_features


def _extract_numeric_features(
    df: pd.DataFrame, numeric_cols: set[str]
) -> tuple[pd.DataFrame, list[dict], list[str]]:
    operations: list[dict] = []
    new_features: list[str] = []

    for col in numeric_cols:
        series = df[col]

        new_cols = [
            f"{col}_squared",
            f"{col}_cubed",
            f"{col}_log",
            f"{col}_sqrt",
        ]

        df[f"{col}_squared"] = series ** 2
        df[f"{col}_cubed"] = series ** 3
        safe_series = series.clip(lower=0).fillna(0)
        df[f"{col}_log"] = np.log1p(safe_series)
        df[f"{col}_sqrt"] = np.sqrt(safe_series)

        new_features.extend(new_cols)
        operations.append({
            "operation": "numeric_transformation",
            "column": str(col),
            "new_features": new_cols,
            "strategy": "polynomial_log_sqrt",
            "detail": f"Created {len(new_cols)} numeric features from '{col}'.",
        })

    return df, operations, new_features


def _extract_interaction_features(
    df: pd.DataFrame, numeric_cols: set[str], corr_threshold: float = 0.3
) -> tuple[pd.DataFrame, list[dict], list[str]]:
    operations: list[dict] = []
    new_features: list[str] = []

    col_list = sorted(numeric_cols)
    if len(col_list) < 2:
        return df, operations, new_features

    for i, col1 in enumerate(col_list):
        for col2 in col_list[i + 1:]:
            if col1 not in df.columns or col2 not in df.columns:
                continue
            corr = df[col1].corr(df[col2])
            if pd.isna(corr):
                continue
            if abs(corr) >= corr_threshold:
                product_col = f"{col1}_x_{col2}"
                ratio_col = f"{col1}_div_{col2}"

                s1 = df[col1].fillna(0)
                s2 = df[col2].fillna(0)

                df[product_col] = s1 * s2

                s2_safe = s2.replace(0, np.nan)
                df[ratio_col] = (s1 / s2_safe).fillna(0)

                new_features.extend([product_col, ratio_col])
                operations.append({
                    "operation": "interaction_features",
                    "column": f"{col1}, {col2}",
                    "new_features": [product_col, ratio_col],
                    "strategy": "product_ratio",
                    "detail": f"Created product and ratio features for correlated columns '{col1}' and '{col2}' (corr={corr:.3f}).",
                })

    return df, operations, new_features


def _extract_categorical_features(
    df: pd.DataFrame, categorical_cols: set[str]
) -> tuple[pd.DataFrame, list[dict], list[str]]:
    operations: list[dict] = []
    new_features: list[str] = []

    for col in categorical_cols:
        freq = df[col].value_counts(normalize=True)
        df[f"{col}_freq"] = df[col].map(freq).fillna(0)
        new_features.append(f"{col}_freq")

        df[f"{col}_label"] = pd.factorize(df[col])[0]
        new_features.append(f"{col}_label")

        operations.append({
            "operation": "categorical_encoding",
            "column": str(col),
            "new_features": [f"{col}_freq", f"{col}_label"],
            "strategy": "frequency_label_encoding",
            "detail": f"Created frequency and label encoding features for '{col}'.",
        })

    return df, operations, new_features


def _apply_feature_selection(
    df: pd.DataFrame, new_feature_names: list[str]
) -> tuple[pd.DataFrame, list[dict], list[str]]:
    operations: list[dict] = []
    removed_features: list[str] = []

    if len(df) == 0:
        return df, operations, removed_features

    new_feature_set = set(new_feature_names)

    # 1. Missing value filter (> 50% missing)
    missing_pct = df.isnull().mean()
    high_missing = missing_pct[missing_pct > 0.5].index.tolist()
    if high_missing:
        df = df.drop(columns=high_missing)
        removed_features.extend([c for c in high_missing if c in new_feature_set])
        operations.append({
            "operation": "missing_value_filter",
            "column": None,
            "new_features": [],
            "strategy": "remove_gt_50_pct_missing",
            "affected_rows": len(df),
            "detail": f"Removed {len(high_missing)} columns with >50% missing values.",
        })

    # 2. Variance threshold (variance < 0.01)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols and len(df) > 1:
        variances = df[numeric_cols].var()
        low_var = variances[variances < 0.01].index.tolist()
        if low_var:
            df = df.drop(columns=low_var)
            removed_features.extend([c for c in low_var if c in new_feature_set])
            operations.append({
                "operation": "variance_threshold",
                "column": None,
                "new_features": [],
                "strategy": "remove_low_variance",
                "affected_rows": len(df),
                "detail": f"Removed {len(low_var)} columns with variance < 0.01.",
            })

    # 3. Correlation filter (|corr| > 0.95, keep higher variance)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) >= 2 and len(df) > 1:
        corr_matrix = df[numeric_cols].corr()
        to_remove: set[str] = set()
        for i in range(len(numeric_cols)):
            if numeric_cols[i] in to_remove:
                continue
            for j in range(i + 1, len(numeric_cols)):
                if numeric_cols[j] in to_remove:
                    continue
                corr_val = corr_matrix.iloc[i, j]
                if pd.notna(corr_val) and abs(corr_val) > 0.95:
                    var_i = df[numeric_cols[i]].var()
                    var_j = df[numeric_cols[j]].var()
                    if pd.isna(var_i) or pd.isna(var_j):
                        continue
                    if var_i >= var_j:
                        to_remove.add(numeric_cols[j])
                    else:
                        to_remove.add(numeric_cols[i])
        if to_remove:
            df = df.drop(columns=list(to_remove))
            removed_features.extend([c for c in to_remove if c in new_feature_set])
            operations.append({
                "operation": "correlation_filter",
                "column": None,
                "new_features": [],
                "strategy": "remove_high_correlation",
                "affected_rows": len(df),
                "detail": f"Removed {len(to_remove)} highly correlated columns (>0.95).",
            })

    surviving_features = [f for f in new_feature_names if f in df.columns]
    return df, operations, surviving_features


def engineer_features(source_file_path: str, upload_dir: str) -> dict:
    if not os.path.exists(source_file_path):
        raise FileNotFoundError(f"Source file not found: {source_file_path}")

    df = read_file(source_file_path)
    rows_before = len(df)
    columns_before = len(df.columns)

    df = df.copy()
    original_columns = list(df.columns)

    datetime_cols, numeric_cols, text_cols, categorical_cols = _classify_columns(
        df, original_columns
    )

    all_operations: list[dict] = []
    all_new_features: list[str] = []

    df, ops, feats = _extract_datetime_features(df, datetime_cols)
    all_operations.extend(ops)
    all_new_features.extend(feats)

    df, ops, feats = _extract_text_features(df, text_cols)
    all_operations.extend(ops)
    all_new_features.extend(feats)

    df, ops, feats = _extract_numeric_features(df, numeric_cols)
    all_operations.extend(ops)
    all_new_features.extend(feats)

    df, ops, feats = _extract_interaction_features(df, numeric_cols)
    all_operations.extend(ops)
    all_new_features.extend(feats)

    df, ops, feats = _extract_categorical_features(df, categorical_cols)
    all_operations.extend(ops)
    all_new_features.extend(feats)

    features_added = len(all_new_features)

    df, ops, surviving_features = _apply_feature_selection(df, all_new_features)
    all_operations.extend(ops)

    features_removed = len(all_new_features) - len(surviving_features)

    rows_after = len(df)
    columns_after = len(df.columns)

    engineered_filename = _generate_engineered_filename(source_file_path)
    engineered_file_path = os.path.join(upload_dir, engineered_filename)
    _save_engineered_file(df, engineered_file_path)

    return {
        "source_file_path": source_file_path,
        "engineered_file_path": engineered_file_path,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "columns_before": columns_before,
        "columns_after": columns_after,
        "features_added": features_added,
        "features_removed": features_removed,
        "new_feature_names": surviving_features,
        "feature_engineering_operations": all_operations,
        "engineering_status": "completed",
    }
