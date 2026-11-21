import type { Schemas } from "@/lib/api";

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

// WebSocket messages. OpenAPI has no WebSocket routes; the backend adds these models to the schema (sibyl.schemas.ws).
export type Review = Schemas["ReviewResult"];
export type ReviewResults = Schemas["ReviewResults"];
export type SocketError = Schemas["SocketError"];
/** Anything sent on /ws/session/{id}. */
export type ReviewSessionMessage = Schemas["ReviewProgress"] | Schemas["ReviewCompleted"] | SocketError;
/** Anything sent on /ws/pull: engine progress lines, then status "success", or an error. */
export type PullProgress = Schemas["PullProgress"];
export type PullMessage = PullProgress | SocketError;
