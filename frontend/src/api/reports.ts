import { apiRequest } from "./client";
import type {
  ReportGenerationRequest,
  ReportGenerationResponse,
  ReportListResponse,
  ReportResponse,
  GlobalReportListResponse,
} from "../types/api";

export function generateReport(request: ReportGenerationRequest): Promise<ReportGenerationResponse> {
  return apiRequest<ReportGenerationResponse>("/reports/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function listDatasetReports(datasetId: number | string): Promise<ReportListResponse> {
  return apiRequest<ReportListResponse>(`/datasets/${datasetId}/reports`);
}

/**
 * Fetch all reports across every dataset and experiment owned by the current user.
 * Supports optional filtering and pagination query parameters.
 */
export interface GlobalReportFilters {
  report_type?: string;
  status?: string;
  dataset_id?: number;
  experiment_id?: number;
  skip?: number;
  limit?: number;
}

export function listGlobalReports(
  filters?: GlobalReportFilters,
): Promise<GlobalReportListResponse> {
  const params = new URLSearchParams();
  if (filters?.report_type) params.set("report_type", filters.report_type);
  if (filters?.status) params.set("status", filters.status);
  if (filters?.dataset_id !== undefined) params.set("dataset_id", String(filters.dataset_id));
  if (filters?.experiment_id !== undefined) params.set("experiment_id", String(filters.experiment_id));
  if (filters?.skip !== undefined) params.set("skip", String(filters.skip));
  if (filters?.limit !== undefined) params.set("limit", String(filters.limit));

  const query = params.toString();
  const url = query ? `/reports?${query}` : "/reports";
  return apiRequest<GlobalReportListResponse>(url);
}

export function getGlobalReport(reportId: number | string): Promise<ReportResponse> {
  return apiRequest<ReportResponse>(`/reports/${reportId}`);
}