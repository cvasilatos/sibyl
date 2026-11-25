"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { useCurrentUser } from "@/hooks/use-current-user";
import { toast } from "@/hooks/use-toast";
import { api, type ReviewSubmission } from "@/lib/api";
import { invalidates, isActiveJob, queries } from "@/lib/api/queries";
import type { ReviewJob, ReviewJobStatus, ReviewResults, ReviewStep } from "@/lib/types";

/** Literature sources the backend can search for related work. */
export type RelatedSource = "arxiv" | "semantic_scholar";

/** Where the selected review is: the steps it goes through and the latest update. */
export interface ReviewProgressState {
  /** The steps this run takes, in order. */
  steps: ReviewStep[];
  /** The step in progress, or the one that failed. */
  current: ReviewStep | null;
  /** Overall progress, 0–100. */
  percent: number;
  message: string;
  outcome: ReviewJobStatus;
  /** Place in the queue while waiting (1 = next). */
  position: number | null;
  filename: string;
}

function progressOf(job: ReviewJob): ReviewProgressState {
  return {
    steps: job.steps ?? [],
    current: job.step ?? null,
    percent: job.progress ?? 0,
    message: job.message ?? "",
    outcome: job.status,
    position: job.position ?? null,
    filename: job.filename,
  };
}

/**
 * Submits reviews to the server's queue and follows them. Reviews run on the server, so closing or reloading the
 * page does not stop them: the queue is read again and the user's newest review is shown.
 */
export function useReviewJobs() {
  const queryClient = useQueryClient();
  const user = useCurrentUser();
  const jobs = useQuery(queries.reviewJobs()).data?.jobs;
  const [chosenJobId, setChosenJobId] = useState<string | null>(null);

  const mine = (jobs ?? []).filter((job) => job.owner === user?.username);
  // The chosen review, or else the user's newest one (e.g. after reopening the page).
  const selectedJob = (jobs ?? []).find((job) => job.id === chosenJobId) ?? mine.at(-1) ?? null;

  // Tell the user when one of their reviews finishes (only for changes seen here, not on the first read).
  const lastStatus = useRef<Map<string, ReviewJobStatus> | null>(null);
  useEffect(() => {
    if (!jobs || !user) return;
    const previous = lastStatus.current;
    lastStatus.current = new Map(jobs.map((job) => [job.id, job.status]));
    if (!previous) return;
    let completed = false;
    for (const job of jobs) {
      const before = previous.get(job.id);
      if (job.owner !== user.username || before === undefined || !isActiveJob({ status: before })) continue;
      if (job.status === "completed") {
        completed = true;
        toast({ title: "✅ Review Complete", description: `"${job.results?.paper_title ?? job.filename}"` });
      } else if (job.status === "failed") {
        toast({ title: "Review Failed", description: job.message || "The review failed.", variant: "destructive" });
      }
    }
    if (completed) queryClient.invalidateQueries(invalidates.reviews);
  }, [jobs, user, queryClient]);

  const submit = useMutation({
    mutationFn: (submission: ReviewSubmission) => api.submitReview(submission),
    onSuccess: (job) => {
      setChosenJobId(job.id);
      queryClient.invalidateQueries(invalidates.reviewJobs);
      toast({
        title: job.status === "queued" ? "Review Queued" : "Review Started",
        description:
          job.status === "queued" && job.position
            ? `${job.filename} is #${job.position} in the queue. It keeps running if you close this page.`
            : `${job.filename}. It keeps running if you close this page.`,
      });
    },
    onError: (error) =>
      toast({ title: "Upload Failed", description: error.message || "An error occurred", variant: "destructive" }),
  });

  const cancel = useMutation({
    mutationFn: (jobId: string) => api.cancelReviewJob(jobId),
    onSuccess: () => queryClient.invalidateQueries(invalidates.reviewJobs),
    onError: (error) => toast({ title: "Could Not Cancel", description: error.message, variant: "destructive" }),
  });

  const { mutateAsync } = submit;
  const start = useCallback(
    async (submission: ReviewSubmission) => {
      try {
        await mutateAsync(submission);
        return true;
      } catch {
        return false; // reported by onError
      }
    },
    [mutateAsync],
  );

  const results: ReviewResults | null = selectedJob?.status === "completed" ? (selectedJob.results ?? null) : null;

  return {
    jobs: jobs ?? [],
    selectedJob,
    selectJob: setChosenJobId,
    progress: selectedJob ? progressOf(selectedJob) : null,
    results,
    isSubmitting: submit.isPending,
    start,
    cancel: cancel.mutate,
    cancellingId: cancel.isPending ? (cancel.variables ?? null) : null,
  };
}
