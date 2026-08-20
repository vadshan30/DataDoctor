import { apiRequest } from "./client";
import type { ExperimentCreateRequest, ExperimentListResponse, ExperimentResponse } from "../types/api";

export function createExperiment(
  datasetId: number | string,
  request: ExperimentCreateRequest
): Promise<ExperimentResponse> {
  return apiRequest<ExperimentResponse>(`/datasets/${datasetId}/experiments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function listExperiments(datasetId: number | string): Promise<ExperimentListResponse> {
  return apiRequest<ExperimentListResponse>(`/datasets/${datasetId}/experiments`);
}

export function getExperiment(
  datasetId: number | string,
  experimentId: number | string
): Promise<ExperimentResponse> {
  return apiRequest<ExperimentResponse>(`/datasets/${datasetId}/experiments/${experimentId}`);
}
