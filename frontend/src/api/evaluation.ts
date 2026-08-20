import { apiRequest } from "./client";
import type {
  EvaluationSummaryResponse,
  ExperimentResponse,
  ModelComparisonResponse,
  ModelEvaluationResponse,
} from "../types/api";

export function evaluateExperiment(
  datasetId: number | string,
  experimentId: number | string
): Promise<ExperimentResponse> {
  return apiRequest<ExperimentResponse>(`/datasets/${datasetId}/experiments/${experimentId}/evaluate`, {
    method: "POST",
  });
}

export function getEvaluationSummary(
  datasetId: number | string,
  experimentId: number | string
): Promise<EvaluationSummaryResponse> {
  return apiRequest<EvaluationSummaryResponse>(`/datasets/${datasetId}/experiments/${experimentId}/evaluation`);
}

export function getModelEvaluation(
  datasetId: number | string,
  experimentId: number | string,
  modelId: number | string
): Promise<ModelEvaluationResponse> {
  return apiRequest<ModelEvaluationResponse>(`/datasets/${datasetId}/experiments/${experimentId}/models/${modelId}/evaluation`);
}

export function getModelComparison(
  datasetId: number | string,
  experimentId: number | string
): Promise<ModelComparisonResponse> {
  return apiRequest<ModelComparisonResponse>(`/datasets/${datasetId}/experiments/${experimentId}/comparison`);
}