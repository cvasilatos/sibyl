import type { ReviewConfig, ReviewDetail, ReviewMode } from "@/lib/types";

export const DETAIL_LABELS: Record<ReviewDetail, string> = {
  auto: "Model decides",
  concise: "Concise",
  standard: "Standard",
  detailed: "Detailed",
};

export const MODE_LABELS: Record<ReviewMode, string> = {
  single: "Whole review at once",
  sections: "Section by section",
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)} s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes} min ${Math.round(seconds % 60)} s`;
}

function formLabel(config: ReviewConfig): string {
  if (config.form === "conference") return `${config.conference ?? "Conference"} reviewer form`;
  if (config.form === "custom") return config.review_form_name ? `Custom form: ${config.review_form_name}` : "Custom form";
  return "Sibyl default";
}

/** The settings that produced a review, as label/value pairs in display order. */
export function reviewConfigRows(config: ReviewConfig): [label: string, value: string][] {
  const calls = config.generation_calls === 1 ? "1 call" : `${config.generation_calls} calls`;
  const rows: [string, string][] = [
    ["Model", config.model],
    ["Engine", config.engine],
    ["Review length", DETAIL_LABELS[config.detail]],
    ["Generation", `${MODE_LABELS[config.mode]} (${calls})`],
    ["Review form", formLabel(config)],
    ["Temperature", String(config.temperature)],
    ["Context window", `${config.context_length.toLocaleString()} tokens${config.paper_truncated ? " (paper end trimmed)" : ""}`],
    ["Figures", config.vlm_model ? `${config.vlm_model} (${config.figures_described ?? 0} described)` : "Not described (captions only)"],
    ["Related work search", config.related_work ? "On" : "Off"],
    ["GPU", config.gpu === null || config.gpu === undefined ? "Auto" : `GPU ${config.gpu}`],
  ];
  if (config.duration_seconds !== null && config.duration_seconds !== undefined) rows.push(["Time taken", formatDuration(config.duration_seconds)]);
  return rows;
}
