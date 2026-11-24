"use client";

import { CheckCircle2, Circle, XCircle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import type { ReviewStep } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useReview } from "./review-context";

const STEP_LABELS: Record<ReviewStep, string> = {
  parse: "Parse the PDF: extract text and figure images",
  figures: "Describe figures with the vision model",
  related_work: "Search arXiv & Semantic Scholar for related work",
  review: "Write the review",
  save: "Save the review",
};

type StepState = "done" | "active" | "failed" | "pending";

function stepState(index: number, currentIndex: number, outcome: "running" | "completed" | "failed"): StepState {
  if (outcome === "completed" || index < currentIndex) return "done";
  if (index === currentIndex) return outcome === "failed" ? "failed" : "active";
  return "pending";
}

function StepIcon({ state }: { state: StepState }) {
  if (state === "done") return <CheckCircle2 className="h-4 w-4 text-primary" aria-hidden />;
  if (state === "active") return <Spinner className="text-primary" label="In progress" />;
  if (state === "failed") return <XCircle className="h-4 w-4 text-destructive" aria-hidden />;
  return <Circle className="h-4 w-4 text-muted-foreground/50" aria-hidden />;
}

/** The steps of the running (or last) review with an overall progress bar, shown under the paper dropzone. */
export default function ReviewProgressPanel() {
  const { progress } = useReview();
  if (!progress) return null;
  const { steps, current, percent, message, outcome } = progress;
  const currentIndex = current ? steps.indexOf(current) : -1;

  return (
    <section aria-label="Review progress" className="space-y-3 rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="font-medium">
          {outcome === "completed" ? "Review complete" : outcome === "failed" ? "Review failed" : "Reviewing…"}
        </span>
        <span className="tabular-nums text-muted-foreground">{percent}%</span>
      </div>
      <Progress
        value={percent}
        aria-label="Overall review progress"
        className={cn(outcome === "failed" && "bg-destructive/20 [&>div]:bg-destructive")}
      />
      {steps.length > 0 && (
        <ol className="space-y-2">
          {steps.map((step, index) => {
            const state = stepState(index, currentIndex, outcome);
            return (
              <li key={step} data-state={state} className="flex items-start gap-2 text-sm">
                <span className="mt-0.5 shrink-0">
                  <StepIcon state={state} />
                </span>
                <div className="min-w-0">
                  <div
                    className={cn(state === "pending" && "text-muted-foreground", state === "active" && "font-medium")}
                  >
                    {STEP_LABELS[step]}
                  </div>
                  {(state === "active" || state === "failed") && (
                    <div
                      className={cn(
                        "break-words text-xs",
                        state === "failed" ? "text-destructive" : "text-muted-foreground",
                      )}
                    >
                      {message}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
      {/* Before the first step (uploading) or a failure outside any step (connection lost), show the message alone. */}
      {currentIndex === -1 && outcome !== "completed" && (
        <p className={cn("text-xs", outcome === "failed" ? "text-destructive" : "text-muted-foreground")}>{message}</p>
      )}
    </section>
  );
}
