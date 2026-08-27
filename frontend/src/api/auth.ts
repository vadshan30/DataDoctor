import { apiRequest } from "./client";
import type { AuthResponse } from "../types/api";

export function login(email: string, password: string) {
  return apiRequest<AuthResponse>(`/auth/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`, { method: "POST" });
}

export function register(email: string, password: string, fullName: string) {
  const params = new URLSearchParams({ email, password });
  if (fullName) params.set("full_name", fullName);
  return apiRequest<{ id: number; email: string }>(`/auth/register?${params}`, { method: "POST" });
}

export function guest() {
  return apiRequest<AuthResponse>("/auth/guest", { method: "POST" });
}
