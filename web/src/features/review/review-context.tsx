"use client";

import { useQuery } from "@tanstack/react-query";
import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";
import { toast } from "@/hooks/use-toast";
import { queries } from "@/lib/api/queries";
import { useReviewSession } from "./use-review-session";

const REVIEW_FORM_EXTENSIONS = [".txt", ".md", ".markdown"];
const REVIEW_FORM_MAX_BYTES = 64 * 1024;

/** Why a custom review form file is rejected, or null when it is acceptable. */
export function reviewFormProblem(file: File): string | null {
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!REVIEW_FORM_EXTENSIONS.includes(extension)) return "Choose a .txt, .md, or .markdown file.";
  if (file.size > REVIEW_FORM_MAX_BYTES) return "The review form must be 64 KiB or smaller.";
  return null;
}

function useReviewState() {
  const session = useReviewSession();
  const { clearResults } = session;
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedReviewForm, setSelectedReviewForm] = useState<File | null>(null);
  const [selectedConferenceId, setSelectedConferenceId] = useState<string | null>(null);
  const [chosenModel, setSelectedModel] = useState("");
  const [chosenGpuIndex, setSelectedGpuIndex] = useState<number | null>(null);

  // A choice that is no longer offered (model removed, GPU gone) falls back to the first model / automatic GPU choice.
  const installed = useQuery(queries.installedModels()).data;
  const availableModels = useMemo(() => installed?.map((model) => model.model) ?? [], [installed]);
  const selectedModel = availableModels.includes(chosenModel) ? chosenModel : (availableModels[0] ?? "");
  const gpus = useQuery(queries.gpus()).data;
  const availableGpus = useMemo(() => (gpus?.available ? gpus.gpus : []), [gpus]);
  const selectedGpuIndex = availableGpus.some((gpu) => gpu.index === chosenGpuIndex) ? chosenGpuIndex : null;

  const selectFile = useCallback(
    (file: File) => {
      if (file.type !== "application/pdf") {
        toast({ title: "Invalid File", description: "Please select a PDF file", variant: "destructive" });
        return;
      }
      setSelectedFile(file);
      clearResults();
    },
    [clearResults]
  );

  const selectReviewForm = useCallback(
    (file: File | null) => {
      if (file) {
        const problem = reviewFormProblem(file);
        if (problem) {
          toast({ title: "Invalid Review Form", description: problem, variant: "destructive" });
          return;
        }
        setSelectedConferenceId(null);
        clearResults();
      }
      setSelectedReviewForm(file);
    },
    [clearResults]
  );

  const selectConference = useCallback(
    (conferenceId: string | null) => {
      setSelectedConferenceId(conferenceId);
      if (conferenceId) setSelectedReviewForm(null);
      clearResults();
    },
    [clearResults]
  );

  const { start } = session;
  const startReview = useCallback(() => {
    if (!selectedFile || !selectedModel) {
      toast({ title: "Cannot Start Review", description: "Select a PDF and an installed model first.", variant: "destructive" });
      return;
    }
    start({ file: selectedFile, reviewForm: selectedReviewForm, conferenceId: selectedConferenceId, model: selectedModel, gpuIndex: selectedGpuIndex });
  }, [start, selectedFile, selectedReviewForm, selectedConferenceId, selectedModel, selectedGpuIndex]);

  return useMemo(
    () => ({
      selectedFile,
      selectFile,
      selectedReviewForm,
      selectReviewForm,
      selectedConferenceId,
      selectConference,
      availableModels,
      selectedModel,
      setSelectedModel,
      availableGpus,
      selectedGpuIndex,
      setSelectedGpuIndex,
      results: session.results,
      isReviewing: session.isReviewing,
      startReview,
    }),
    [
      selectedFile,
      selectFile,
      selectedReviewForm,
      selectReviewForm,
      selectedConferenceId,
      selectConference,
      availableModels,
      selectedModel,
      availableGpus,
      selectedGpuIndex,
      session.results,
      session.isReviewing,
      startReview,
    ]
  );
}

type ReviewState = ReturnType<typeof useReviewState>;

const ReviewContext = createContext<ReviewState | undefined>(undefined);

/** Holds the review draft (paper, form, model, GPU) and the running session. Lives in the root layout so both survive page changes. */
export function ReviewProvider({ children }: { children: ReactNode }) {
  return <ReviewContext.Provider value={useReviewState()}>{children}</ReviewContext.Provider>;
}

export function useReview(): ReviewState {
  const context = useContext(ReviewContext);
  if (context === undefined) throw new Error("useReview must be used within a ReviewProvider");
  return context;
}
