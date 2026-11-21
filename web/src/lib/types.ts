import type { Schemas } from "@/lib/api";

export type AppTab = "review" | "library" | "models" | "gpu";

// Backend models, generated from the OpenAPI schema (see src/lib/api/schema.d.ts). Do not redefine them here.
export type ReviewCriteria = Schemas["ReviewCriteria"];
export type ConferenceSummary = Schemas["ConferenceSummary"];
export type EngineInfo = Schemas["EngineInfo"];
export type StoredReview = Schemas["Review"];
export type FullReview = Schemas["FullReview"];
export type ReviewsResponse = Schemas["ReviewList"];
export type ReviewStatistics = Schemas["ReviewStatistics"];
export type InstalledModel = Schemas["InstalledModel"];
export type AvailableModel = Schemas["AvailableModel"];
export type GpuProcess = Schemas["GpuProcess"];
export type GpuStats = Schemas["GpuStats"];
export type GpuResponse = Schemas["GpuList"];

// Frontend-only types. Review and ReviewResults arrive over the review WebSocket, which OpenAPI doesn't describe.
export interface Review {
  paper_title: string;
  reviewer_model: string;
  criteria: ReviewCriteria;
  raw_response: string;
}

export interface ReviewResults {
  paper_title: string;
  reviews: Review[];
}

export type GpuSummary = Pick<GpuStats, "index" | "name" | "gpu_utilization" | "memory_used" | "memory_total">;
