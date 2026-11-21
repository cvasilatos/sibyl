"use client";

import { useQuery } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import { Spinner } from "@/components/ui/spinner";
import { queries } from "@/lib/api/queries";
import ConferenceSelect from "./ConferenceSelect";
import CustomFormPicker from "./CustomFormPicker";
import PaperDropzone from "./PaperDropzone";
import { useReview } from "./review-context";

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
            <NativeSelect id="model-select" value={review.selectedModel} onChange={(e) => review.setSelectedModel(e.target.value)} disabled={review.isReviewing}>
              {review.availableModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </NativeSelect>
            <p className="text-xs text-muted-foreground">This will override the default model configured in your environment</p>
          </div>
        )}

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

        <ConferenceSelect />
        <CustomFormPicker />

        <Button onClick={review.startReview} disabled={!review.selectedFile || review.isReviewing} className="w-full" size="lg">
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
