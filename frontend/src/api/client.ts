const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = localStorage.getItem("datadoctor_token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (response.status === 401) {
    localStorage.removeItem("datadoctor_token");
    window.dispatchEvent(new Event("datadoctor:unauthorized"));
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail || "Something went wrong. Please try again.";
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}

export { API_BASE_URL };
