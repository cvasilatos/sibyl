"use client";

import { useQuery } from "@tanstack/react-query";
import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";
import { toast } from "@/hooks/use-toast";
import { queries } from "@/lib/api/queries";
import { type FormRef, formKey, parseFormKey } from "@/lib/review-forms";
import type { ReviewDetail, ReviewMode } from "@/lib/types";
import { useReviewSession } from "./use-review-session";

/** Vision-model choices besides installed models: use the server's configured default, or skip figure descriptions. */
export const VLM_DEFAULT = "";
export const VLM_NONE = "none";

function useReviewState() {
  const session = useReviewSession();
  const { clearResults } = session;
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [chosenForm, setChosenForm] = useState<FormRef | null>(null);
  const [chosenModel, setSelectedModel] = useState("");
  const [chosenVlm, setSelectedVlm] = useState(VLM_DEFAULT);
  const [chosenGpuIndex, setSelectedGpuIndex] = useState<number | null>(null);
  const [relatedWork, setRelatedWork] = useState(true);
  // Unset until the user picks one: follow the server defaults (SIBYL_REVIEW_DETAIL / SIBYL_REVIEW_MODE).
  const [chosenDetail, setSelectedDetail] = useState<ReviewDetail | null>(null);
  const [chosenMode, setSelectedMode] = useState<ReviewMode | null>(null);
  const serviceConfig = useQuery(queries.serviceConfig()).data;
  const selectedDetail: ReviewDetail = chosenDetail ?? serviceConfig?.review_detail ?? "auto";
  const selectedMode: ReviewMode = chosenMode ?? serviceConfig?.review_mode ?? "single";

  // A choice that is no longer offered (model removed, GPU gone) falls back to the first model / automatic GPU choice.
  const installed = useQuery(queries.installedModels()).data;
  const availableModels = useMemo(() => installed?.map((model) => model.model) ?? [], [installed]);
  const selectedModel = availableModels.includes(chosenModel) ? chosenModel : (availableModels[0] ?? "");
  const selectedVlm = chosenVlm === VLM_DEFAULT || chosenVlm === VLM_NONE || availableModels.includes(chosenVlm) ? chosenVlm : VLM_DEFAULT;
  const gpus = useQuery(queries.gpus()).data;
  const availableGpus = useMemo(() => (gpus?.available ? gpus.gpus : []), [gpus]);
  const selectedGpuIndex = availableGpus.some((gpu) => gpu.index === chosenGpuIndex) ? chosenGpuIndex : null;
  // A saved form deleted in the Review Forms tab falls back to the generic review.
  const savedForms = useQuery(queries.reviewForms()).data;
  const selectedForm = chosenForm?.kind === "custom" && savedForms && !savedForms.some((form) => form.id === chosenForm.id) ? null : chosenForm;
  const selectedFormKey = selectedForm ? formKey(selectedForm) : null;

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

  /** Pick a review form by its key ("conference:<id>" or "custom:<id>"), or null for the generic review. */
  const selectForm = useCallback(
    (key: string | null) => {
      setChosenForm(parseFormKey(key));
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
    start({
      file: selectedFile,
      form: selectedForm,
      model: selectedModel,
      vlm: selectedVlm,
      relatedWork,
      gpuIndex: selectedGpuIndex,
      detail: selectedDetail,
      mode: selectedMode,
    });
  }, [start, selectedFile, selectedForm, selectedModel, selectedVlm, relatedWork, selectedGpuIndex, selectedDetail, selectedMode]);

  return useMemo(
    () => ({
      selectedFile,
      selectFile,
      selectedFormKey,
      selectedFormKind: selectedForm?.kind ?? null,
      selectForm,
      availableModels,
      selectedModel,
      setSelectedModel,
      selectedDetail,
      setSelectedDetail,
      selectedMode,
      setSelectedMode,
      selectedVlm,
      setSelectedVlm,
      relatedWork,
      setRelatedWork,
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
      selectedFormKey,
      selectedForm,
      selectForm,
      availableModels,
      selectedModel,
      selectedDetail,
      selectedMode,
      selectedVlm,
      relatedWork,
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

/** Holds the review draft (paper, form, models, GPU) and the running session. Lives in the root layout so both survive page changes. */
export function ReviewProvider({ children }: { children: ReactNode }) {
  return <ReviewContext.Provider value={useReviewState()}>{children}</ReviewContext.Provider>;
}

export function useReview(): ReviewState {
  const context = useContext(ReviewContext);
  if (context === undefined) throw new Error("useReview must be used within a ReviewProvider");
  return context;
}
