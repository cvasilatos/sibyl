"use client";

import { Ban, Eye, ListOrdered, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { canManage, useCurrentUser } from "@/hooks/use-current-user";
import { isActiveJob } from "@/lib/api/queries";
import type { ReviewJob } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useReview } from "./review-context";

function statusText(job: ReviewJob): string {
  switch (job.status) {
    case "queued":
      return job.position ? `Queued #${job.position}` : "Queued";
    case "running":
      return `${job.gpu != null ? `GPU ${job.gpu} · ` : ""}${job.progress ?? 0}%`;
    case "completed":
      return "Complete";
    case "failed":
      return "Failed";
    default:
      return "Cancelled";
  }
}

const STATUS_STYLE: Record<ReviewJob["status"], string> = {
  queued: "bg-muted text-muted-foreground",
  running: "bg-primary/10 text-primary",
  completed: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
  failed: "bg-destructive/10 text-destructive",
  cancelled: "bg-muted text-muted-foreground",
};

/**
 * Every review waiting or running on the server (anyone's), and the user's finished ones. Reviews keep running when
 * the page closes, so this is where they are found again.
 */
export default function ReviewQueue() {
  const { jobs, selectedJob, selectJob, cancelJob, cancellingJobId } = useReview();
  const user = useCurrentUser();
  if (jobs.length === 0) return null;
  const activeCount = jobs.filter(isActiveJob).length;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <ListOrdered className="h-4 w-4" />
          Review Queue
          <span className="text-sm font-normal text-muted-foreground">
            {activeCount === 0 ? "nothing running" : `${activeCount} waiting or running`}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="divide-y" aria-label="Review queue">
          {jobs.map((job) => {
            const mine = job.owner === user?.username;
            const selected = job.id === selectedJob?.id;
            const active = isActiveJob(job);
            return (
              <li
                key={job.id}
                aria-label={`${job.filename} by ${job.owner}`}
                aria-current={selected ? "true" : undefined}
                className={cn("flex flex-wrap items-center gap-x-3 gap-y-1 py-2 text-sm", selected && "font-medium")}
              >
                <span className={cn("rounded px-2 py-0.5 text-xs tabular-nums", STATUS_STYLE[job.status])}>
                  {statusText(job)}
                </span>
                <span className="min-w-0 flex-1 truncate" title={job.filename}>
                  {job.filename}
                </span>
                <span className="text-xs text-muted-foreground">
                  {mine ? "you" : job.owner} · {job.model}
                  {job.form_name ? ` · ${job.form_name}` : ""}
                </span>
                <span className="flex gap-1">
                  {!selected && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => selectJob(job.id)}
                      aria-label={`Show ${job.filename}`}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  )}
                  {canManage(user, job.owner) && (
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={cancellingJobId === job.id}
                      onClick={() =>
                        (!active || window.confirm(`Cancel the review of ${job.filename}?`)) && cancelJob(job.id)
                      }
                      aria-label={active ? `Cancel ${job.filename}` : `Dismiss ${job.filename}`}
                    >
                      {cancellingJobId === job.id ? (
                        <Spinner label="Cancelling" />
                      ) : active ? (
                        <Ban className="h-4 w-4" />
                      ) : (
                        <X className="h-4 w-4" />
                      )}
                    </Button>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
