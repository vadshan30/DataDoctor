import { apiRequest } from "./client";
import type { DataQualityResponse } from "../types/api";

export function getDatasetQuality(datasetId: number | string): Promise<DataQualityResponse> {
  return apiRequest<DataQualityResponse>(`/datasets/${datasetId}/quality`);
}
