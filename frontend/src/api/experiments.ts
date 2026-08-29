import { apiRequest } from "./client";
import type { ExperimentCreateRequest, ExperimentListResponse, ExperimentResponse, GlobalExperimentListResponse } from "../types/api";

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

/**
 * Fetch all experiments across every dataset owned by the current user.
 * Supports optional filtering and pagination query parameters.
 */
export interface GlobalExperimentFilters {
  q?: string;
  status?: string;
  dataset_id?: number;
  skip?: number;
  limit?: number;
}

export function listGlobalExperiments(
  filters?: GlobalExperimentFilters,
): Promise<GlobalExperimentListResponse> {
  const params = new URLSearchParams();
  if (filters?.q) params.set("q", filters.q);
  if (filters?.status) params.set("status", filters.status);
  if (filters?.dataset_id !== undefined) params.set("dataset_id", String(filters.dataset_id));
  if (filters?.skip !== undefined) params.set("skip", String(filters.skip));
  if (filters?.limit !== undefined) params.set("limit", String(filters.limit));

  const query = params.toString();
  const url = query ? `/experiments?${query}` : "/experiments";
  return apiRequest<GlobalExperimentListResponse>(url);
}

export function getGlobalExperiment(experimentId: number | string): Promise<ExperimentResponse> {
  return apiRequest<ExperimentResponse>(`/experiments/${experimentId}`);
}
