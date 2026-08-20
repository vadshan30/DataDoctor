import { apiRequest } from "./client";
import type { CleaningResultListResponse, CleaningResultResponse } from "../types/api";

export function cleanDataset(datasetId: number | string): Promise<CleaningResultResponse> {
  return apiRequest<CleaningResultResponse>(`/datasets/${datasetId}/clean`, {
    method: "POST",
  });
}

export function getCleanedDatasets(datasetId: number | string): Promise<CleaningResultListResponse> {
  return apiRequest<CleaningResultListResponse>(`/datasets/${datasetId}/cleaned`);
}
