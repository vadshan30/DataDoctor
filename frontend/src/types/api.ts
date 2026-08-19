export interface User {
  id: number;
  email: string;
  full_name?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  email: string;
}

export interface Dataset {
  dataset_id: number;
  name: string;
  description?: string | null;
  file_type: string;
  file_size: number;
  row_count: number;
  column_count: number;
  version: number;
  status: string;
  owner_id: number;
  created_at: string;
  updated_at: string;
}

export interface DatasetListResponse {
  datasets: Dataset[];
  total: number;
}

export interface UploadResponse {
  message: string;
  dataset: Dataset;
}
