import { apiRequest } from "./client";
import type { DatasetProfileResponse } from "../types/api";

export function getDatasetProfile(datasetId: number | string): Promise<DatasetProfileResponse> {
  return apiRequest<DatasetProfileResponse>(`/datasets/${datasetId}/profile`);
}
