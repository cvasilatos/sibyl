import { API_URL } from "@/lib/config";
import type {
  AvailableModel,
  FullReview,
  GpuResponse,
  InstalledModel,
  ReviewsResponse,
  ReviewStatistics,
} from "@/lib/types";

interface ModelsResponse<T> {
  models: T[];
  count: number;
}

interface ModelTagsResponse {
  model: string;
  tags: string[];
}

interface UploadResponse {
  session_id: string;
  filename: string;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload && typeof payload.detail === "string" ? payload.detail : `Request failed with status ${response.status}`;
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listInstalledModels: () => requestJson<ModelsResponse<InstalledModel>>("/api/models"),
  listAvailableModels: () => requestJson<ModelsResponse<AvailableModel>>("/api/models/available"),
  listModelTags: (modelName: string) => requestJson<ModelTagsResponse>(`/api/models/available/${encodeURIComponent(modelName)}/tags`),
  listGpus: () => requestJson<GpuResponse>("/api/gpu"),
  listReviews: (limit = 50) => requestJson<ReviewsResponse>(`/api/reviews?limit=${limit}`),
  getReview: (reviewId: string, signal?: AbortSignal) => requestJson<FullReview>(`/api/reviews/${encodeURIComponent(reviewId)}`, { signal }),
  getStatistics: () => requestJson<ReviewStatistics>("/api/statistics"),
  deleteReview: (reviewId: string) => requestJson<{ message: string; id: string }>(`/api/reviews/${encodeURIComponent(reviewId)}`, { method: "DELETE" }),
  deleteAllReviews: () => requestJson<{ message: string; count: number }>("/api/reviews", { method: "DELETE" }),
  async downloadReviewPdf(reviewId: string): Promise<Blob> {
    const response = await fetch(`${API_URL}/api/reviews/${encodeURIComponent(reviewId)}/pdf`);
    if (!response.ok) throw new Error("Failed to download PDF");
    return response.blob();
  },
  async uploadPaper(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    return requestJson<UploadResponse>("/api/upload", { method: "POST", body: formData });
  },
};

