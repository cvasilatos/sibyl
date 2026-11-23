import createClient from "openapi-fetch";
import { API_URL } from "@/lib/config";
import type { FormRef } from "@/lib/review-forms";
import type { components, paths } from "./schema";

/** Response and request models from the backend, generated into schema.d.ts by `npm run gen:api`. */
export type Schemas = components["schemas"];

/** Typed client for the backend. Paths, parameters and responses are checked against the backend's OpenAPI schema. */
// fetch is looked up on each call rather than captured once, so tests (and polyfills) can replace it.
export const client = createClient<paths>({ baseUrl: API_URL, fetch: (request) => globalThis.fetch(request) });

type Result<T> = { data?: T; error?: unknown; response: Response };

/** Return the response body, or throw the backend's `detail` message (or the status) as an Error. */
async function unwrap<T>(request: Promise<Result<T>>): Promise<T> {
  const { data, error, response } = await request;
  if (error !== undefined || data === undefined) {
    const detail = typeof error === "object" && error !== null && "detail" in error ? error.detail : undefined;
    throw new Error(typeof detail === "string" ? detail : `Request failed with status ${response.status}`);
  }
  return data;
}

export const api = {
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
  /** Upload a paper to review against a conference template or a saved custom form, or neither. */
  uploadPaper(file: File, form?: FormRef | null) {
    const formData = new FormData();
    formData.append("file", file);
    if (form?.kind === "conference") formData.append("conference_id", form.id);
    else if (form?.kind === "custom") formData.append("review_form_id", form.id);
    // FormData goes through as-is; the generated body type describes the same multipart fields.
    return unwrap(client.POST("/api/upload", { body: formData as never, bodySerializer: (body) => body }));
  },
};
