import { cn } from "@/lib/utils";

/** Colour for a free-text recommendation: green for accept, red for reject, yellow otherwise (borderline, revise, …). */
export function recommendationClassName(recommendation: string): string {
  const normalized = recommendation.toLowerCase();
  if (normalized.includes("accept")) return "text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-950";
  if (normalized.includes("reject")) return "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950";
  return "text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-950";
}

export default function RecommendationBadge({
  recommendation,
  size = "sm",
}: {
  recommendation: string;
  size?: "sm" | "md";
}) {
  return (
    <span
      className={cn(
        "rounded-full font-semibold",
        size === "md" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs",
        recommendationClassName(recommendation),
      )}
    >
      {recommendation}
    </span>
  );
}
