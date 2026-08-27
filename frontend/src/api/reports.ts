import { apiRequest } from "./client";
import type { ReportGenerationRequest, ReportGenerationResponse } from "../types/api";

export function generateReport(request: ReportGenerationRequest): Promise<ReportGenerationResponse> {
  return apiRequest<ReportGenerationResponse>(`/reports/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}
