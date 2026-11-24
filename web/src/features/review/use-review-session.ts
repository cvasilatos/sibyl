"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { invalidates } from "@/lib/api/queries";
import { getWebSocketUrl } from "@/lib/config";
import type { FormRef } from "@/lib/review-forms";
import type { ReviewDetail, ReviewMode, ReviewResults, ReviewSessionMessage, ReviewStep } from "@/lib/types";

/** Literature sources the backend can search for related work. */
export type RelatedSource = "arxiv" | "semantic_scholar";

export interface ReviewRequest {
  file: File;
  /** Conference template or saved custom form to answer, or null for the generic review. */
  form: FormRef | null;
  model: string;
  /** Vision model that describes figures: "" for the server default, "none" to skip figures. */
  vlm: string;
  /** Where to search for related work so the reviewer can judge novelty against it; empty skips the search. */
  relatedSources: RelatedSource[];
  /** GPU to run on, or null to let the backend pick. */
  gpuIndex: number | null;
  /** How long the review should be (guidance in the prompt, not a token limit). */
  detail: ReviewDetail;
  /** Write the whole review in one call, or one call per section. */
  mode: ReviewMode;
}

/** Where the current (or last) review run is: the steps it goes through and the latest update. */
export interface ReviewProgressState {
  /** The steps this run takes, in order; empty until the backend has announced them (while uploading). */
  steps: ReviewStep[];
  /** The step in progress, or the one that failed. */
  current: ReviewStep | null;
  /** Overall progress, 0–100. */
  percent: number;
  message: string;
  outcome: "running" | "completed" | "failed";
}

/** Uploads a paper and follows its review over the session WebSocket, reporting progress on the page and in a toast. */
export function useReviewSession() {
  const queryClient = useQueryClient();
  const [results, setResults] = useState<ReviewResults | null>(null);
  const [isReviewing, setIsReviewing] = useState(false);
  const [progress, setProgress] = useState<ReviewProgressState | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  // Close the socket without reporting a failure when the provider unmounts.
  useEffect(
    () => () => {
      const socket = socketRef.current;
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    },
    [],
  );

  const start = useCallback(
    async ({ file, form, model, vlm, relatedSources, gpuIndex, detail, mode }: ReviewRequest) => {
      setIsReviewing(true);
      setResults(null);
      setProgress({ steps: [], current: null, percent: 0, message: "Uploading the paper...", outcome: "running" });
      try {
        const upload = await api.uploadPaper(file, form);
        // The backend numbers hosts from 1; 0 means "any".
        const hostIndex = gpuIndex !== null ? gpuIndex + 1 : 0;
        const progressToast = toast({
          title: "Review in Progress",
          description: `Starting review of ${file.name}...`,
          duration: Number.POSITIVE_INFINITY,
        });
        const params = new URLSearchParams({
          model,
          host: String(hostIndex),
          related: String(relatedSources.length > 0),
          sources: relatedSources.join(","),
          detail,
          mode,
        });
        if (vlm) params.set("vlm", vlm);
        const socket = new WebSocket(`${getWebSocketUrl()}/ws/session/${upload.session_id}?${params}`);
        socketRef.current = socket;
        let finished = false;

        const fail = (message: string) => {
          if (finished) return;
          finished = true;
          setIsReviewing(false);
          setProgress((state) => state && { ...state, message, outcome: "failed" });
          progressToast.dismiss();
          toast({ title: "Review Failed", description: message, variant: "destructive" });
        };

        socket.onmessage = (event) => {
          let message: ReviewSessionMessage;
          try {
            message = JSON.parse(event.data) as ReviewSessionMessage;
          } catch {
            fail("The review service returned an invalid response.");
            socket.close();
            return;
          }

          if (message.status === "started") {
            setProgress((state) => state && { ...state, steps: message.steps, message: "Starting the review..." });
          } else if (message.status === "progress") {
            const { step, progress: percent, message: text } = message;
            setProgress((state) => state && { ...state, current: step, percent, message: text });
            progressToast.update({
              id: progressToast.id,
              title: "Review in Progress",
              description: `${file.name}: ${message.progress}% — ${message.message}`,
              duration: Number.POSITIVE_INFINITY,
            });
          } else if (message.status === "completed") {
            finished = true;
            setIsReviewing(false);
            setResults(message.results);
            setProgress(
              (state) =>
                state && { ...state, current: null, percent: 100, message: message.message, outcome: "completed" },
            );
            progressToast.dismiss();
            toast({
              title: "✅ Review Complete",
              description: `"${message.results.paper_title}" — ID: ${message.review_id}`,
            });
            queryClient.invalidateQueries(invalidates.reviews);
            socket.close();
          } else if (message.status === "error") {
            fail(message.message || "The review failed.");
            socket.close();
          }
        };
        socket.onerror = () => fail("Failed to connect to review service. Please try again.");
        socket.onclose = () => {
          socketRef.current = null;
          if (!finished) fail("The review connection closed unexpectedly.");
        };
      } catch (error) {
        setIsReviewing(false);
        setProgress(null);
        toast({
          title: "Upload Failed",
          description: error instanceof Error ? error.message : "An error occurred",
          variant: "destructive",
        });
      }
    },
    [queryClient],
  );

  const clearResults = useCallback(() => {
    setResults(null);
    setProgress(null);
  }, []);

  return { results, isReviewing, progress, start, clearResults };
}
