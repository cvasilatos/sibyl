import { FileText, FileUp, Loader2, Upload, X } from "lucide-react";
import type { RefObject } from "react";
import GpuLoadSummary from "@/components/GpuLoadSummary";
import { Button } from "@/components/ui/button";

type Props = {
  selectedFile: File | null;
  selectedReviewForm: File | null;
  onReviewFormChange: (file: File | null) => void;
  selectedModel: string;
  availableModels: string[];
  onModelChange: (model: string) => void;
  availableGpus: Array<{ index: number; name: string }>;
  selectedGpuIndex: number | null;
  onGpuChange: (gpuIndex: number | null) => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
  reviewFormInputRef: RefObject<HTMLInputElement | null>;
  isDragging: boolean;
  handleDragOver: (e: React.DragEvent) => void;
  handleDragLeave: (e: React.DragEvent) => void;
  handleDrop: (e: React.DragEvent) => void;
  handleFileInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleReviewFormInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  startReview: (gpuIndex: number | null) => Promise<void>;
  isReviewing: boolean;
};

export default function UploadArea({
  selectedFile,
  selectedReviewForm,
  onReviewFormChange,
  selectedModel,
  availableModels,
  onModelChange,
  availableGpus,
  selectedGpuIndex,
  onGpuChange,
  fileInputRef,
  reviewFormInputRef,
  isDragging,
  handleDragOver,
  handleDragLeave,
  handleDrop,
  handleFileInputChange,
  handleReviewFormInputChange,
  startReview,
  isReviewing,
}: Props) {
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-[7fr_3fr] gap-4 items-start">
        {/* Left 70%: PDF upload area */}
        <button
          type="button"
          className={`w-full border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-all ${
            isDragging ? "border-primary bg-primary/5 scale-[1.02]" : "border-border hover:border-primary hover:bg-accent"
          } ${selectedFile ? "border-green-500 bg-green-50 dark:bg-green-950" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
          }}
        >
          <input ref={fileInputRef} type="file" accept=".pdf" onChange={handleFileInputChange} className="hidden" />
          <FileText className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
          <p className="text-lg font-medium mb-2">{selectedFile ? `Selected: ${selectedFile.name}` : "Drag and drop a PDF file here or click to browse"}</p>
          <p className="text-sm text-muted-foreground">{selectedFile ? `Size: ${(selectedFile.size / 1024 / 1024).toFixed(2)} MB` : "Supports research papers in PDF format"}</p>
        </button>

        {/* Right 30%: Model/GPU selection and review button */}
        <div className="flex flex-col gap-4">
          {availableModels.length > 0 && (
            <div className="space-y-2">
              <label htmlFor="model-select" className="text-sm font-medium">
                Select Model for Review
              </label>
              <select
                id="model-select"
                value={selectedModel}
                onChange={(e) => onModelChange(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-input rounded-md bg-background"
                disabled={isReviewing}
              >
                {availableModels.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">This will override the default model configured in your environment</p>
            </div>
          )}

          {availableGpus.length > 0 && (
            <div className="space-y-2">
              <label htmlFor="gpu-select" className="text-sm font-medium">
                Select GPU
              </label>
              <select
                id="gpu-select"
                value={selectedGpuIndex ?? "auto"}
                onChange={(e) => onGpuChange(e.target.value === "auto" ? null : Number(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-input rounded-md bg-background"
                disabled={isReviewing}
              >
                <option value="auto">Auto</option>
                {availableGpus.map((gpu) => (
                  <option key={gpu.index} value={gpu.index}>
                    GPU {gpu.index}: {gpu.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">Choose which GPU host to use for this review run</p>
            </div>
          )}

          <div className="space-y-2">
            <label htmlFor="review-form-input" className="text-sm font-medium">
              Review Form (Optional)
            </label>
            <input
              ref={reviewFormInputRef}
              id="review-form-input"
              type="file"
              accept=".txt,.md,.markdown,text/plain,text/markdown"
              onChange={handleReviewFormInputChange}
              className="hidden"
              disabled={isReviewing}
            />
            {selectedReviewForm ? (
              <div className="flex items-center gap-2 rounded-md border border-input px-3 py-2">
                <FileText className="h-4 w-4 shrink-0 text-primary" />
                <span className="min-w-0 flex-1 truncate text-sm" title={selectedReviewForm.name}>
                  {selectedReviewForm.name}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => onReviewFormChange(null)}
                  disabled={isReviewing}
                  aria-label="Remove review form"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <Button type="button" variant="outline" className="w-full" onClick={() => reviewFormInputRef.current?.click()} disabled={isReviewing}>
                <FileUp className="mr-2 h-4 w-4" />
                Upload Review Form
              </Button>
            )}
            <p className="text-xs text-muted-foreground">TXT or Markdown, up to 64 KiB. The model will complete its sections.</p>
          </div>

          <Button onClick={() => startReview(selectedGpuIndex)} disabled={!selectedFile || isReviewing} className="w-full" size="lg">
            {isReviewing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
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

      {/* Live GPU load */}
      <GpuLoadSummary />
    </>
  );
}
