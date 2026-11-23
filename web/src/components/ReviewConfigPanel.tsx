import { reviewConfigRows } from "@/lib/review-config";
import type { ReviewConfig } from "@/lib/types";

/** The settings a review was produced with, collapsed by default. */
export default function ReviewConfigPanel({ config }: { config: ReviewConfig }) {
  return (
    <details className="rounded-md bg-muted p-3 text-sm">
      <summary className="cursor-pointer font-semibold">⚙️ Settings used for this review</summary>
      <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-[max-content_1fr]" aria-label="Review settings">
        {reviewConfigRows(config).map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-muted-foreground">{label}</dt>
            <dd className="break-words font-medium">{value}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
