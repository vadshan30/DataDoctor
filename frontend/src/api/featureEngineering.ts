import { apiRequest } from "./client";
import type { EngineeringResultListResponse, EngineeringResultResponse } from "../types/api";

export function engineerFeatures(datasetId: number | string): Promise<EngineeringResultResponse> {
  return apiRequest<EngineeringResultResponse>(`/datasets/${datasetId}/engineer_features`, {
    method: "POST",
  });
}

export function getEngineeredDatasets(datasetId: number | string): Promise<EngineeringResultListResponse> {
  return apiRequest<EngineeringResultListResponse>(`/datasets/${datasetId}/engineered`);
}
