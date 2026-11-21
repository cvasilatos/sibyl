"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { invalidates } from "@/lib/api/queries";
import { getWebSocketUrl } from "@/lib/config";
import type { ReviewResults } from "@/lib/types";

interface ReviewSocketMessage {
  status: "progress" | "completed" | "error";
  progress?: number;
  message?: string;
  review_id?: string;
  results?: ReviewResults;
}

export interface ReviewRequest {
  file: File;
  reviewForm: File | null;
  conferenceId: string | null;
  model: string;
  /** GPU to run on, or null to let the backend pick. */
  gpuIndex: number | null;
}

/** Uploads a paper and follows its review over the session WebSocket, reporting progress in a toast. */
export function useReviewSession() {
  const queryClient = useQueryClient();
  const [results, setResults] = useState<ReviewResults | null>(null);
  const [isReviewing, setIsReviewing] = useState(false);
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
    []
  );

  const start = useCallback(
    async ({ file, reviewForm, conferenceId, model, gpuIndex }: ReviewRequest) => {
      setIsReviewing(true);
      setResults(null);
      try {
        const upload = await api.uploadPaper(file, reviewForm, conferenceId);
        // The backend numbers hosts from 1; 0 means "any".
        const hostIndex = gpuIndex !== null ? gpuIndex + 1 : 0;
        const progressToast = toast({ title: "Review in Progress", description: `Starting review of ${file.name}...`, duration: Number.POSITIVE_INFINITY });
        const params = new URLSearchParams({ model, host: String(hostIndex) });
        const socket = new WebSocket(`${getWebSocketUrl()}/ws/session/${upload.session_id}?${params}`);
        socketRef.current = socket;
        let finished = false;

        const fail = (message: string) => {
          if (finished) return;
          finished = true;
          setIsReviewing(false);
          progressToast.dismiss();
          toast({ title: "Review Failed", description: message, variant: "destructive" });
        };

        socket.onmessage = (event) => {
          let message: ReviewSocketMessage;
          try {
            message = JSON.parse(event.data) as ReviewSocketMessage;
          } catch {
            fail("The review service returned an invalid response.");
            socket.close();
            return;
          }

          if (message.status === "progress") {
            progressToast.update({
              id: progressToast.id,
              title: "Review in Progress",
              description: `${file.name}: ${message.progress ?? 0}% — ${message.message ?? "Working..."}`,
              duration: Number.POSITIVE_INFINITY,
            });
          } else if (message.status === "completed" && message.results) {
            finished = true;
            setIsReviewing(false);
            setResults(message.results);
            progressToast.dismiss();
            toast({ title: "✅ Review Complete", description: `"${message.results.paper_title}" — ID: ${message.review_id ?? "N/A"}` });
            queryClient.invalidateQueries(invalidates.reviews);
            socket.close();
          } else if (message.status === "error") {
            fail(message.message ?? "The review failed.");
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
        toast({ title: "Upload Failed", description: error instanceof Error ? error.message : "An error occurred", variant: "destructive" });
      }
    },
    [queryClient]
  );

  const clearResults = useCallback(() => setResults(null), []);

  return { results, isReviewing, start, clearResults };
}
