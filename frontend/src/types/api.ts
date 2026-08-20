export interface User {
  id: number;
  email: string;
  full_name?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  email: string;
}

export interface Dataset {
  dataset_id: number;
  name: string;
  description?: string | null;
  file_type: string;
  file_size: number;
  row_count: number;
  column_count: number;
  version: number;
  status: string;
  owner_id: number;
  created_at: string;
  updated_at: string;
}

export interface DatasetListResponse {
  datasets: Dataset[];
  total: number;
}

export interface UploadResponse {
  message: string;
  dataset: Dataset;
}

// ---------------------------------------------------------------------------
// Data profiling types (mirror backend/app/schemas/profiling.py)
// ---------------------------------------------------------------------------

export interface OutlierProfile {
  count: number;
  percentage: number;
  lower_bound: number;
  upper_bound: number;
}

export interface NumericStats {
  min: number | null;
  max: number | null;
  mean: number | null;
  median: number | null;
  standard_deviation: number | null;
  variance: number | null;
  q1: number | null;
  q3: number | null;
  iqr: number | null;
  outliers: OutlierProfile | null;
}

export interface CategoricalStats {
  top_values: (number | string | boolean | null)[];
  top_value_counts: number[];
  top_value_percentage: number[];
}

export interface DatetimeStats {
  min_date: string | null;
  max_date: string | null;
}

export interface ColumnProfile {
  column_name: string;
  data_type: string;
  pandas_dtype: string;
  null_count: number;
  null_percentage: number;
  non_null_count: number;
  unique_count: number;
  unique_percentage: number;
  numeric_stats: NumericStats | null;
  categorical_stats: CategoricalStats | null;
  datetime_stats: DatetimeStats | null;
}

export interface DatasetProfileResponse {
  row_count: number;
  column_count: number;
  duplicate_row_count: number;
  duplicate_row_percentage: number;
  memory_usage: number;
  numerical_column_count: number;
  categorical_column_count: number;
  datetime_column_count: number;
  boolean_column_count: number;
  columns: ColumnProfile[];
}

// ---------------------------------------------------------------------------
// Data quality types (mirror backend/app/schemas/quality.py)
// ---------------------------------------------------------------------------

export type QualitySeverity = "high" | "medium" | "low";

export interface QualityIssue {
  issue_type: string;
  severity: QualitySeverity;
  column_name: string | null;
  description: string;
  metric_value: number | string | null;
}

export interface QualityRecommendation {
  issue_type: string;
  recommendation_text: string;
}

export interface QualitySummary {
  missing_percentage: number;
  duplicate_percentage: number;
  constant_columns: number;
  high_cardinality_columns: number;
  outlier_columns: number;
  suspicious_columns: number;
  potential_identifiers: number;
}

export interface DataQualityResponse {
  dataset_id: number | null;
  quality_score: number;
  summary: QualitySummary;
  issues: QualityIssue[];
  recommendations: QualityRecommendation[];
}

// ---------------------------------------------------------------------------
// Data cleaning types (mirror backend/app/schemas/cleaning.py)
// ---------------------------------------------------------------------------

export interface CleaningOperation {
  operation: string;
  column: string | null;
  affected_rows: number;
  strategy: string | null;
  replacement_value?: unknown;
  detail: string | null;
}

export interface CleaningResultResponse {
  cleaned_dataset_id: number;
  dataset_id: number;
  cleaning_status: string;
  rows_before: number;
  rows_after: number;
  columns_before: number;
  columns_after: number;
  missing_values_handled: number;
  duplicates_removed: number;
  cleaning_operations: CleaningOperation[];
  created_at: string;
}

export interface CleaningResultListResponse {
  cleaned_datasets: CleaningResultResponse[];
  total: number;
}

// ---------------------------------------------------------------------------
// Feature engineering types (mirror backend/app/schemas/feature_engineering.py)
// ---------------------------------------------------------------------------

export interface FeatureEngineeringOperation {
  operation: string;
  column: string | null;
  new_features: string[] | null;
  strategy: string | null;
  affected_rows: number | null;
  replacement_value?: unknown;
  detail: string | null;
}

export interface EngineeringResultResponse {
  engineered_dataset_id: number;
  dataset_id: number;
  cleaned_dataset_id: number | null;
  engineering_status: string;
  rows_before: number;
  rows_after: number;
  columns_before: number;
  columns_after: number;
  features_added: number;
  features_removed: number;
  new_feature_names: string[];
  feature_engineering_operations: FeatureEngineeringOperation[];
  created_at: string;
}

export interface EngineeringResultListResponse {
  engineered_datasets: EngineeringResultResponse[];
  total: number;
}

