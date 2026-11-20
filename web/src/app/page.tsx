"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { type ChangeEvent, type DragEvent, Suspense, useCallback, useState } from "react";
import GpuMonitor from "@/components/GpuMonitor";
import ModelManager from "@/components/ModelManager";
import ResultsPanel from "@/components/ResultsPanel";
import ReviewLibrary from "@/components/ReviewLibrary";
import Tabs from "@/components/Tabs";
import UploadArea from "@/components/UploadArea";
import type { AppTab } from "@/lib/types";
import { useReviewWorkflow } from "@/lib/use-review-workflow";

const APP_TABS: AppTab[] = ["review", "library", "models", "gpu"];

export default function Home() {
  return (
    <Suspense fallback={null}>
      <HomeContent />
    </Suspense>
  );
}

function HomeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const tabParam = searchParams.get("tab");
  const reviewParam = searchParams.get("review");
  const activeTab: AppTab = APP_TABS.includes(tabParam as AppTab) ? (tabParam as AppTab) : "review";
  const review = useReviewWorkflow(activeTab);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileInputChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file) review.selectFile(file);
    },
    [review.selectFile]
  );

  const handleReviewFormInputChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file) review.selectReviewForm(file);
    },
    [review.selectReviewForm]
  );

  const handleDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((event: DragEvent) => {
    event.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();
      setIsDragging(false);
      const file = event.dataTransfer.files?.[0];
      if (file) review.selectFile(file);
    },
    [review.selectFile]
  );

  const handleReviewExpand = useCallback(
    (reviewId: string | null) => {
      const query = reviewId ? `&review=${encodeURIComponent(reviewId)}` : "";
      router.push(`/?tab=library${query}`);
    },
    [router]
  );

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="border-b bg-card px-4 md:px-8 py-4">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-3xl">🔮</span>
          <div>
            <h1 className="text-xl font-bold leading-tight">Sibyl</h1>
            <p className="text-sm text-muted-foreground">AI-Powered Research Paper Review</p>
          </div>
        </div>
        <Tabs activeTab={activeTab} />
      </header>

      <main className="flex-1 px-4 md:px-8 py-6 space-y-6">
        {activeTab === "review" && (
          <UploadArea
            selectedFile={review.selectedFile}
            selectedReviewForm={review.selectedReviewForm}
            onReviewFormChange={review.selectReviewForm}
            selectedModel={review.selectedModel}
            availableModels={review.availableModels}
            onModelChange={review.setSelectedModel}
            availableGpus={review.availableGpus}
            selectedGpuIndex={review.selectedGpuIndex}
            onGpuChange={review.setSelectedGpuIndex}
            fileInputRef={review.fileInputRef}
            reviewFormInputRef={review.reviewFormInputRef}
            isDragging={isDragging}
            handleDragOver={handleDragOver}
            handleDragLeave={handleDragLeave}
            handleDrop={handleDrop}
            handleFileInputChange={handleFileInputChange}
            handleReviewFormInputChange={handleReviewFormInputChange}
            startReview={review.startReview}
            isReviewing={review.isReviewing}
          />
        )}

        {activeTab === "library" && <ReviewLibrary initialExpandedReview={reviewParam} onReviewExpand={handleReviewExpand} />}
        {activeTab === "models" && <ModelManager />}
        {activeTab === "gpu" && <GpuMonitor />}
        {review.results && <ResultsPanel results={review.results} maxScore={review.maxScore} />}
      </main>

      <footer className="border-t px-4 py-3 text-center">
        <p className="text-xs text-muted-foreground">Powered by local LLMs via Ollama • Privacy-first • Zero-cost</p>
      </footer>
    </div>
  );
}
