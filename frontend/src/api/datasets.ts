import { apiRequest } from "./client";
import type { Dataset, DatasetListResponse, UploadResponse } from "../types/api";

export function listDatasets() {
  return apiRequest<DatasetListResponse>("/datasets/");
}

export async function getDataset(datasetId: string) {
  const response = await listDatasets();
  const dataset = response.datasets.find((item) => String(item.dataset_id) === datasetId);
  if (!dataset) throw new Error("Dataset not found.");
  return dataset;
}

export function uploadDataset(file: File, description?: string, onProgress?: (value: number) => void) {
  const form = new FormData();
  form.append("file", file);
  if (description) form.append("description", description);
  onProgress?.(50);
  return apiRequest<UploadResponse>("/datasets/upload", { method: "POST", body: form }).finally(() => onProgress?.(100));
}
