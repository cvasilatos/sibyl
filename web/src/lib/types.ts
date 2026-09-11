export type AppTab = "review" | "library" | "models" | "gpu";

export interface ReviewCriteria {
  novelty: string;
  methodology: string;
  results: string;
  clarity: string;
  impact: string;
  limitations: string;
  strengths: string;
  score: number;
  recommendation: string;
  detailed_feedback: string;
  review_form_response?: string | null;
}

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

export interface StoredReview {
  id: string;
  paper_title: string;
  pdf_filename: string;
  pdf_path: string | null;
  reviewer_model: string;
  score: number;
  recommendation: string;
  review_summary: string;
  created_at: string;
}

export interface FullReview extends Omit<StoredReview, "review_summary"> {
  criteria: ReviewCriteria;
  raw_response: string;
}

export interface ReviewsResponse {
  reviews: StoredReview[];
  total: number;
  limit: number;
  offset: number;
}

export interface ReviewStatistics {
  total_reviews: number;
  unique_papers: number;
  unique_models: number;
  recommendations: Record<string, number>;
}

export interface InstalledModel {
  model: string;
  size: number;
  modified_at: string;
  digest: string;
}

export interface AvailableModel {
  name: string;
  description: string;
  size: string;
  installed: boolean;
  installed_variants?: string[];
}

export interface GpuProcess {
  pid: number;
  name: string;
  memory_bytes: number;
  type: "compute" | "graphics";
}

export interface GpuStats {
  index: number;
  name: string;
  gpu_utilization: number;
  memory_utilization: number;
  memory_used: number;
  memory_total: number;
  memory_free: number;
  temperature: number | null;
  power_usage_watts: number | null;
  power_limit_watts: number | null;
  fan_speed_percent: number | null;
  processes: GpuProcess[];
}

export interface GpuResponse {
  gpus: GpuStats[];
  count: number;
  available: boolean;
}

export type GpuSummary = Pick<GpuStats, "index" | "name" | "gpu_utilization" | "memory_used" | "memory_total">;
