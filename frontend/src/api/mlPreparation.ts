import { apiRequest } from "./client";
import type { MLReadyDatasetListResponse, MLReadyDatasetResponse, PrepareRequest } from "../types/api";

export function prepareMLDataset(
  datasetId: number | string,
  request: PrepareRequest
): Promise<MLReadyDatasetResponse> {
  return apiRequest<MLReadyDatasetResponse>(`/datasets/${datasetId}/prepare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function getPreparedDatasets(datasetId: number | string): Promise<MLReadyDatasetListResponse> {
  return apiRequest<MLReadyDatasetListResponse>(`/datasets/${datasetId}/prepared`);
}

export function getLatestPreparedDataset(datasetId: number | string): Promise<MLReadyDatasetResponse> {
  return apiRequest<MLReadyDatasetResponse>(`/datasets/${datasetId}/prepared/latest`);
}
