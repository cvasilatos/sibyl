import createClient from "openapi-fetch";
import { API_URL } from "@/lib/config";
import type { FormRef } from "@/lib/review-forms";
import type { components, paths } from "./schema";

/** Response and request models from the backend, generated into schema.d.ts by `npm run gen:api`. */
export type Schemas = components["schemas"];

/** Typed client for the backend. Paths, parameters and responses are checked against the backend's OpenAPI schema. */
// fetch is looked up on each call rather than captured once, so tests (and polyfills) can replace it. The session
// cookie goes with every request (the API runs on another port of the same host).
export const client = createClient<paths>({
  baseUrl: API_URL,
  credentials: "include",
  fetch: (request) => globalThis.fetch(request),
});

type Result<T> = { data?: T; error?: unknown; response: Response };

/** Thrown for a 401: nobody is signed in, or the sign-in expired. The app shows the sign-in page. */
export class UnauthorizedError extends Error {
  constructor(message = "Sign in to use Sibyl") {
    super(message);
    this.name = "UnauthorizedError";
  }
}

/** Return the response body, or throw the backend's `detail` message (or the status) as an Error. */
async function unwrap<T>(request: Promise<Result<T>>): Promise<T> {
  const { data, error, response } = await request;
  if (error !== undefined || data === undefined) {
    const detail = typeof error === "object" && error !== null && "detail" in error ? error.detail : undefined;
    const message = typeof detail === "string" ? detail : `Request failed with status ${response.status}`;
    throw response.status === 401 ? new UnauthorizedError(message) : new Error(message);
  }
  return data;
}

/** What to review and how: the paper, the form it answers and the user's choices. */
export interface ReviewSubmission {
  file: File;
  /** Conference template or saved custom form to answer, or null for the generic review. */
  form: FormRef | null;
  model: string;
  /** Vision model that describes figures: "" for the server default, "none" to skip figures. */
  vlm: string;
  /** Where to search for related work; empty skips the search. */
  relatedSources: string[];
  /** GPU to run on, or null for the first free one. */
  gpuIndex: number | null;
  detail: Schemas["ReviewDetail"];
  mode: Schemas["ReviewMode"];
}

export const api = {
  /** The signed-in user, or null when nobody is signed in. */
  async getCurrentUser() {
    try {
      return await unwrap(client.GET("/api/auth/me"));
    } catch (error) {
      if (error instanceof UnauthorizedError) return null;
      throw error;
    }
  },
  login: (username: string, password: string) =>
    unwrap(client.POST("/api/auth/login", { body: { username, password } })),
  logout: () => unwrap(client.POST("/api/auth/logout")),
  getConfig: () => unwrap(client.GET("/api/config")),
  /** The top of the overall score scale, validated so the UI can divide by it. */
  async getMaxScore(): Promise<number> {
    const { max_score: maxScore } = await api.getConfig();
    if (typeof maxScore !== "number" || maxScore <= 0) throw new Error("Invalid max_score in config response");
    return maxScore;
  },
  getEngine: () => unwrap(client.GET("/api/engine")),
  listConferences: () => unwrap(client.GET("/api/conferences")),
  getConference: (conferenceId: string, signal?: AbortSignal) =>
    unwrap(
      client.GET("/api/conferences/{conference_id}", { params: { path: { conference_id: conferenceId } }, signal }),
    ),
  listReviewForms: () => unwrap(client.GET("/api/review-forms")),
  getReviewForm: (formId: string, signal?: AbortSignal) =>
    unwrap(client.GET("/api/review-forms/{form_id}", { params: { path: { form_id: formId } }, signal })),
  saveReviewForm(name: string, file: File) {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("file", file);
    return unwrap(client.POST("/api/review-forms", { body: formData as never, bodySerializer: (body) => body }));
  },
  deleteReviewForm: (formId: string) =>
    unwrap(client.DELETE("/api/review-forms/{form_id}", { params: { path: { form_id: formId } } })),
  listInstalledModels: () => unwrap(client.GET("/api/models")),
  deleteModel: (modelName: string) =>
    unwrap(client.DELETE("/api/models/{model_name}", { params: { path: { model_name: modelName } } })),
  listAvailableModels: () => unwrap(client.GET("/api/models/available")),
  listModelTags: (modelName: string) =>
    unwrap(client.GET("/api/models/available/{model_name}/tags", { params: { path: { model_name: modelName } } })),
  listGpus: () => unwrap(client.GET("/api/gpu")),
  listReviews: (limit = 50) => unwrap(client.GET("/api/reviews", { params: { query: { limit } } })),
  getReview: (reviewId: string, signal?: AbortSignal) =>
    unwrap(client.GET("/api/reviews/{review_id}", { params: { path: { review_id: reviewId } }, signal })),
  getStatistics: () => unwrap(client.GET("/api/statistics")),
  deleteReview: (reviewId: string) =>
    unwrap(client.DELETE("/api/reviews/{review_id}", { params: { path: { review_id: reviewId } } })),
  deleteAllReviews: () => unwrap(client.DELETE("/api/reviews")),
  async downloadReviewPdf(reviewId: string): Promise<Blob> {
    const { data } = await client.GET("/api/reviews/{review_id}/pdf", {
      params: { path: { review_id: reviewId } },
      parseAs: "blob",
    });
    if (!data) throw new Error("Failed to download PDF");
    return data;
  },
  listReviewJobs: () => unwrap(client.GET("/api/review-jobs")),
  /** Queue a review; it runs on the server whether or not this page stays open. */
  submitReview({ file, form, model, vlm, relatedSources, gpuIndex, detail, mode }: ReviewSubmission) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("model", model);
    if (form?.kind === "conference") formData.append("conference_id", form.id);
    else if (form?.kind === "custom") formData.append("review_form_id", form.id);
    if (gpuIndex !== null) formData.append("gpu", String(gpuIndex));
    if (vlm) formData.append("vlm", vlm);
    formData.append("related", String(relatedSources.length > 0));
    formData.append("sources", relatedSources.join(","));
    formData.append("detail", detail);
    formData.append("mode", mode);
    // FormData goes through as-is; the generated body type describes the same multipart fields.
    return unwrap(client.POST("/api/review-jobs", { body: formData as never, bodySerializer: (body) => body }));
  },
  /** Cancel a queued or running review, or dismiss a finished one. */
  cancelReviewJob: (jobId: string) =>
    unwrap(client.DELETE("/api/review-jobs/{job_id}", { params: { path: { job_id: jobId } } })),
};
