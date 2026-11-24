import type { Schemas } from "@/lib/api";

// Backend models, generated from the OpenAPI schema (see src/lib/api/schema.d.ts). Do not redefine them here.
export type ReviewCriteria = Schemas["ReviewCriteria"];
export type ConferenceSummary = Schemas["ConferenceSummary"];
export type SavedFormSummary = Schemas["SavedFormSummary"];
export type SavedFormDetail = Schemas["SavedFormDetail"];
export type EngineInfo = Schemas["EngineInfo"];
export type StoredReview = Schemas["Review"];
export type FullReview = Schemas["FullReview"];
export type RelatedPaper = Schemas["RelatedPaper"];
export type ReviewConfig = Schemas["ReviewConfig"];
export type ReviewDetail = Schemas["ReviewDetail"];
export type ReviewMode = Schemas["ReviewMode"];
export type ServiceConfig = Schemas["ServiceConfig"];
export type ReviewsResponse = Schemas["ReviewList"];
export type ReviewStatistics = Schemas["ReviewStatistics"];
export type InstalledModel = Schemas["InstalledModel"];
export type AvailableModel = Schemas["AvailableModel"];
export type GpuProcess = Schemas["GpuProcess"];
export type GpuStats = Schemas["GpuStats"];
export type GpuResponse = Schemas["GpuList"];

// WebSocket messages. OpenAPI has no WebSocket routes; the backend adds these models to the schema (sibyl.schemas.ws).
export type Review = Schemas["ReviewResult"];
export type ReviewResults = Schemas["ReviewResults"];
export type SocketError = Schemas["SocketError"];
export type ReviewStarted = Schemas["ReviewStarted"];
/** A stage of the review pipeline (parse, figures, related_work, review, save). */
export type ReviewStep = ReviewStarted["steps"][number];
/** Anything sent on /ws/session/{id}: the planned steps, progress within them, then the results or an error. */
export type ReviewSessionMessage = ReviewStarted | Schemas["ReviewProgress"] | Schemas["ReviewCompleted"] | SocketError;
/** Anything sent on /ws/pull: engine progress lines, then status "success", or an error. */
export type PullProgress = Schemas["PullProgress"];
export type PullMessage = PullProgress | SocketError;
