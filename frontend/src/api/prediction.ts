import { apiRequest } from "./client";
import type {
  PredictionRequest,
  BatchPredictionRequest,
  PredictionResult,
  BatchPredictionResult,
  PredictionRecordListResponse,
  PredictionRecordResponse,
} from "../types/api";

export function predictSingle(
  datasetId: number | string,
  experimentId: number | string,
  modelId: number | string,
  request: PredictionRequest
): Promise<PredictionResult> {
  return apiRequest<PredictionResult>(`/datasets/${datasetId}/experiments/${experimentId}/models/${modelId}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function predictBatch(
  datasetId: number | string,
  experimentId: number | string,
  modelId: number | string,
  request: BatchPredictionRequest
): Promise<BatchPredictionResult> {
  return apiRequest<BatchPredictionResult>(`/datasets/${datasetId}/experiments/${experimentId}/models/${modelId}/predict/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function getModelPredictions(
  datasetId: number | string,
  experimentId: number | string,
  modelId: number | string
): Promise<PredictionRecordListResponse> {
  return apiRequest<PredictionRecordListResponse>(`/datasets/${datasetId}/experiments/${experimentId}/models/${modelId}/predict`);
}

export function getExperimentPredictions(
  datasetId: number | string,
  experimentId: number | string
): Promise<PredictionRecordListResponse> {
  return apiRequest<PredictionRecordListResponse>(`/datasets/${datasetId}/experiments/${experimentId}/predictions`);
}