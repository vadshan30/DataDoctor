import os
import uuid
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.services.data_engine.ingester import DataIngestionError, read_file


class MLPreparationError(Exception):
    pass


def _generate_ml_ready_filename(source_file_path: str) -> str:
    base = os.path.basename(source_file_path)
    name, ext = os.path.splitext(base)
    return f"{name}_ml_ready_{uuid.uuid4().hex}{ext}"


def _save_ml_ready_file(df: pd.DataFrame, file_path: str) -> None:
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


def _is_numeric_column(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def _is_categorical_column(series: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)


class MLPreparationService:
    """
    Produces an ML-ready dataset artifact from an engineered/cleaned source.

    Workflow:
        Input Dataset -> Validate -> Split (train/test) -> Fit preprocessor on
        train only -> Transform train & test -> Persist ML-ready file + metadata.

    No data leakage: scalers/encoders/imputers are fitted EXCLUSIVELY on the
    training split. Test data is only ever transformed, never used for fitting.
    """

    def __init__(
        self,
        source_file_path: str,
        upload_dir: str,
        target_column: str,
        test_size: float = 0.20,
        random_state: int = 42,
    ):
        self.source_file_path = source_file_path
        self.upload_dir = upload_dir
        self.target_column = target_column
        self.test_size = test_size
        self.random_state = random_state
        self.preprocessing_operations: list[dict[str, Any]] = []

    # -- public API ---------------------------------------------------------

    def prepare(self) -> dict[str, Any]:
        if not os.path.exists(self.source_file_path):
            raise FileNotFoundError(f"Source file not found: {self.source_file_path}")

        try:
            df = read_file(self.source_file_path)
        except DataIngestionError as e:
            raise MLPreparationError(f"Failed to read source file: {e}") from e

        rows_before = len(df)
        original_feature_count = len(df.columns) - 1  # exclude target

        # --- Validate target column exists ---------------------------------
        if self.target_column not in df.columns:
            raise MLPreparationError(
                f"Target column '{self.target_column}' does not exist in the dataset."
            )

        # --- Validate target column is not completely empty -----------------
        target_series = df[self.target_column]
        if target_series.isna().all():
            raise MLPreparationError(
                f"Target column '{self.target_column}' is completely empty."
            )

        # --- Validate dataset has enough rows -------------------------------
        if rows_before < 4:
            raise MLPreparationError(
                f"Dataset must contain at least 4 rows for a train/test split "
                f"(current: {rows_before})."
            )

        # --- Separate X and y (target removed from features) ---------------
        feature_columns = [c for c in df.columns if c != self.target_column]
        X = df[feature_columns].copy()
        y = target_series.copy()

        # Drop rows where the *target* is missing (cannot supervise those)
        valid_mask = y.notna()
        X = X.loc[valid_mask].reset_index(drop=True)
        y = y.loc[valid_mask].reset_index(drop=True)

        if len(X) < 4:
            raise MLPreparationError(
                f"Insufficient rows ({len(X)}) after removing missing target rows."
            )

        # --- Determine numeric / categorical feature columns ---------------
        numeric_columns, categorical_columns = self._classify_columns(X)

        # --- Train/Test split (deterministic, reproducible) ----------------
        stratify = y if self._is_stratifiable(y) else None
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=stratify,
        )

        train_rows = len(X_train)
        test_rows = len(X_test)

        # --- Build preprocessor and FIT ONLY ON TRAINING DATA --------------
        self._build_preprocessor(numeric_columns, categorical_columns)

        X_train_processed = self.preprocessor.fit_transform(X_train)
        X_test_processed = self.preprocessor.transform(X_test)

        # --- Recover feature names -----------------------------------------
        feature_names = self._get_feature_names(numeric_columns, categorical_columns)

        # --- Assemble processed DataFrame ----------------------------------
        X_train_df = pd.DataFrame(X_train_processed, columns=feature_names)
        X_test_df = pd.DataFrame(X_test_processed, columns=feature_names)

        # Add a split indicator so train/test rows are distinguishable in the
        # persisted ML-ready file (consumable by a future modelling phase).
        X_train_df.insert(0, "__split__", "train")
        X_test_df.insert(0, "__split__", "test")

        X_combined = pd.concat([X_train_df, X_test_df], ignore_index=True)
        y_combined = pd.concat([y_train, y_test], ignore_index=True)

        # Target column is appended last so it is never mistaken for a feature.
        X_combined[self.target_column] = y_combined.values
        ml_ready_df = X_combined

        rows_after = len(ml_ready_df)
        processed_feature_count = len(feature_names)

        # --- Persist output file -------------------------------------------
        ml_ready_filename = _generate_ml_ready_filename(self.source_file_path)
        ml_ready_file_path = os.path.join(self.upload_dir, ml_ready_filename)

        try:
            _save_ml_ready_file(ml_ready_df, ml_ready_file_path)
        except Exception as e:
            if os.path.exists(ml_ready_file_path):
                os.remove(ml_ready_file_path)
            raise MLPreparationError(f"Failed to save ML-ready file: {e}") from e

        # --- Assemble metadata ---------------------------------------------
        return {
            "source_file_path": self.source_file_path,
            "ml_ready_file_path": ml_ready_file_path,
            "target_column": self.target_column,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "train_rows": train_rows,
            "test_rows": test_rows,
            "original_feature_count": original_feature_count,
            "processed_feature_count": processed_feature_count,
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "feature_names": feature_names,
            "test_size": self.test_size,
            "random_state": self.random_state,
            "preprocessing_operations": self.preprocessing_operations,
            "status": "completed",
        }

    # -- helpers ------------------------------------------------------------

    def _classify_columns(self, X: pd.DataFrame) -> tuple[list[str], list[str]]:
        numeric_columns: list[str] = []
        categorical_columns: list[str] = []
        for col in X.columns:
            if _is_numeric_column(X[col]):
                numeric_columns.append(col)
            elif _is_categorical_column(X[col]):
                categorical_columns.append(col)
            else:
                numeric_columns.append(col)
        return numeric_columns, categorical_columns

    def _is_stratifiable(self, y: pd.Series) -> bool:
        """A target is stratifiable only if every class has >= 2 samples."""
        if pd.api.types.is_numeric_dtype(y):
            return False
        counts = y.value_counts()
        return len(counts) > 1 and (counts >= 2).all()

    def _build_preprocessor(
        self, numeric_columns: list[str], categorical_columns: list[str]
    ) -> None:
        """Build a ColumnTransformer with SimpleImputer + StandardScaler for
        numeric columns and SimpleImputer + OneHotEncoder for categorical
        columns. The preprocessor is stored on ``self`` and must be *fit*
        explicitly on the training split by the caller (see ``prepare``)."""
        transformers: list[tuple[str, Any, list[str]]] = []

        if numeric_columns:
            numeric_pipeline = Pipeline(
                steps=[
                    (
                        "imputer",
                        SimpleImputer(strategy="median"),
                    ),
                    (
                        "scaler",
                        StandardScaler(),
                    ),
                ]
            )
            transformers.append(
                ("num", numeric_pipeline, numeric_columns)
            )
            self.preprocessing_operations.append({
                "operation": "numeric_preprocessing",
                "strategy": "median_imputation+standard_scaling",
                "affected_columns": numeric_columns,
                "detail": "Numeric features handled missing values via "
                          "median imputation and standardized via StandardScaler, "
                          "fitted only on training data.",
                "fit_on": "train",
            })

        if categorical_columns:
            categorical_pipeline = Pipeline(
                steps=[
                    (
                        "imputer",
                        SimpleImputer(strategy="most_frequent"),
                    ),
                    (
                        "encoder",
                        OneHotEncoder(
                            handle_unknown="ignore",
                            sparse_output=False,
                        ),
                    ),
                ]
            )
            transformers.append(
                ("cat", categorical_pipeline, categorical_columns)
            )
            self.preprocessing_operations.append({
                "operation": "categorical_preprocessing",
                "strategy": "most_frequent_imputation+one_hot_encoding",
                "affected_columns": categorical_columns,
                "detail": "Categorical features handled missing values via "
                          "most-frequent imputation and encoded via OneHotEncoder "
                          "(handle_unknown='ignore'), fitted only on training data.",
                "fit_on": "train",
            })

        if not transformers:
            # No features left after separating target — create a passthrough
            transformers.append(("passthrough", "passthrough", []))

        self.preprocessor = ColumnTransformer(
            transformers=transformers, remainder="drop"
        )

    def _get_feature_names(
        self, numeric_columns: list[str], categorical_columns: list[str]
    ) -> list[str]:
        """Retrieve feature names from the fitted ColumnTransformer."""
        names: list[str] = []
        for name, transformer, cols in self.preprocessor.transformers_:
            if name == "num" and cols:
                names.extend(cols)
            elif name == "cat" and cols:
                encoder = transformer.named_steps["encoder"]
                try:
                    enc_names = encoder.get_feature_names_out(cols).tolist()
                except Exception:
                    enc_names = [
                        f"{col}_{v}"
                        for col in cols
                        for v in sorted(encoder.categories_[cols.index(col)])
                    ]
                names.extend(enc_names)
            elif name == "passthrough" and cols:
                names.extend(cols)
        return names if names else numeric_columns + categorical_columns


def prepare_ml_dataset(
    source_file_path: str,
    upload_dir: str,
    target_column: str,
    test_size: float = 0.20,
    random_state: int = 42,
) -> dict[str, Any]:
    service = MLPreparationService(
        source_file_path=source_file_path,
        upload_dir=upload_dir,
        target_column=target_column,
        test_size=test_size,
        random_state=random_state,
    )
    return service.prepare()
