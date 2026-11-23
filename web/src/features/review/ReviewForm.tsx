"use client";

import { useQuery } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import { Spinner } from "@/components/ui/spinner";
import { queries } from "@/lib/api/queries";
import { DETAIL_LABELS, MODE_LABELS } from "@/lib/review-config";
import type { ReviewDetail, ReviewMode } from "@/lib/types";
import PaperDropzone from "./PaperDropzone";
import ReviewFormSelect from "./ReviewFormSelect";
import { useReview, VLM_DEFAULT, VLM_NONE } from "./review-context";

/** The paper dropzone (left) and the review options with the start button (right). */
export default function ReviewForm() {
  const review = useReview();
  // Observing the list here refetches it each time the form opens, to pick up models installed outside Sibyl.
  useQuery(queries.installedModels());

  return (
    <div className="grid grid-cols-1 items-start gap-4 md:grid-cols-[7fr_3fr]">
      <PaperDropzone />

      <div className="flex flex-col gap-4">
        {review.availableModels.length > 0 && (
          <div className="space-y-2">
            <label htmlFor="model-select" className="text-sm font-medium">
              Select Model for Review
            </label>
            <NativeSelect
              id="model-select"
              value={review.selectedModel}
              onChange={(e) => review.setSelectedModel(e.target.value)}
              disabled={review.isReviewing}
            >
              {review.availableModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </NativeSelect>
            <p className="text-xs text-muted-foreground">
              This will override the default model configured in your environment
            </p>
          </div>
        )}

        {review.availableModels.length > 0 && (
          <div className="space-y-2">
            <label htmlFor="vlm-select" className="text-sm font-medium">
              Vision Model for Figures
            </label>
            <NativeSelect
              id="vlm-select"
              value={review.selectedVlm}
              onChange={(e) => review.setSelectedVlm(e.target.value)}
              disabled={review.isReviewing}
            >
              <option value={VLM_DEFAULT}>Server default</option>
              <option value={VLM_NONE}>None (captions only)</option>
              {review.availableModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </NativeSelect>
            <p className="text-xs text-muted-foreground">
              Describes each figure for the reviewer; pick a vision-language model
            </p>
          </div>
        )}

        <div className="space-y-2">
          <label htmlFor="detail-select" className="text-sm font-medium">
            Review Length
          </label>
          <NativeSelect
            id="detail-select"
            value={review.selectedDetail}
            onChange={(e) => review.setSelectedDetail(e.target.value as ReviewDetail)}
            disabled={review.isReviewing}
          >
            {Object.entries(DETAIL_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </NativeSelect>
          <p className="text-xs text-muted-foreground">
            Model decides: no length guidance. The other levels tell the model how much to write; none cuts the review
            off
          </p>
        </div>

        <div className="space-y-2">
          <label htmlFor="mode-select" className="text-sm font-medium">
            Generation
          </label>
          <NativeSelect
            id="mode-select"
            value={review.selectedMode}
            onChange={(e) => review.setSelectedMode(e.target.value as ReviewMode)}
            disabled={review.isReviewing}
          >
            {Object.entries(MODE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </NativeSelect>
          <p className="text-xs text-muted-foreground">
            {review.selectedMode === "sections" && review.selectedFormKind === "custom"
              ? "Custom forms have no fixed sections, so this one is reviewed at once"
              : "Section by section: one call per section, longer reviews from small models, but slower"}
          </p>
        </div>

        <div className="space-y-1">
          <label htmlFor="related-work" className="flex items-center gap-2 text-sm font-medium">
            <input
              id="related-work"
              type="checkbox"
              className="h-4 w-4 accent-primary"
              checked={review.relatedWork}
              onChange={(e) => review.setRelatedWork(e.target.checked)}
              disabled={review.isReviewing}
            />
            Search arXiv for related work
          </label>
          <p className="text-xs text-muted-foreground">
            Judges novelty against prior work. Sends search keywords (never the paper) to arXiv.
          </p>
        </div>

        {review.availableGpus.length > 0 && (
          <div className="space-y-2">
            <label htmlFor="gpu-select" className="text-sm font-medium">
              Select GPU
            </label>
            <NativeSelect
              id="gpu-select"
              value={review.selectedGpuIndex ?? "auto"}
              onChange={(e) => review.setSelectedGpuIndex(e.target.value === "auto" ? null : Number(e.target.value))}
              disabled={review.isReviewing}
            >
              <option value="auto">Auto</option>
              {review.availableGpus.map((gpu) => (
                <option key={gpu.index} value={gpu.index}>
                  GPU {gpu.index}: {gpu.name}
                </option>
              ))}
            </NativeSelect>
            <p className="text-xs text-muted-foreground">Choose which GPU host to use for this review run</p>
          </div>
        )}

        <ReviewFormSelect />

        <Button
          onClick={review.startReview}
          disabled={!review.selectedFile || review.isReviewing}
          className="w-full"
          size="lg"
        >
          {review.isReviewing ? (
            <>
              <Spinner className="mr-2" label="Reviewing" />
              Reviewing…
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              Start Review
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
