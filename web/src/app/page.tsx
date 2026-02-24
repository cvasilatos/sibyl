"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import GpuMonitor from "@/components/GpuMonitor";
import ModelManager from "@/components/ModelManager";
import ResultsPanel from "@/components/ResultsPanel";
import ReviewLibrary from "@/components/ReviewLibrary";
import Tabs from "@/components/Tabs";
import UploadArea from "@/components/UploadArea";
import { toast } from "@/components/ui/use-toast";
import { API_URL, fetchMaxScore, getWebSocketUrl } from "@/lib/config";

interface ReviewCriteria {
  novelty: string;
  methodology: string;
  results: string;
  clarity: string;
  impact: string;
  limitations: string;
  strengths: string;
  score: number;
  recommendation: string;
  detailed_feedback: string;
}

interface Review {
  paper_title: string;
  reviewer_model: string;
  criteria: ReviewCriteria;
  raw_response: string;
}

interface ReviewResults {
  paper_title: string;
  reviews: Review[];
}

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

  const activeTab: "review" | "library" | "models" | "gpu" = tabParam === "review" || tabParam === "library" || tabParam === "models" || tabParam === "gpu" ? tabParam : "review";

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [results, setResults] = useState<ReviewResults | null>(null);
  const [maxScore, setMaxScore] = useState<number>(10);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadModels = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/models`);
      if (response.ok) {
        const data = await response.json();
        const modelNames = data.models.map((m: { name: string }) => m.name);
        setAvailableModels(modelNames);
        if (modelNames.length > 0) {
          setSelectedModel(modelNames[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load models:", err);
    }
  }, []);

  // Load available models and max score on mount
  useEffect(() => {
    loadModels();

    const loadMaxScore = async () => {
      try {
        const score = await fetchMaxScore();
        setMaxScore(score);
      } catch (err) {
        console.error("Failed to load max score:", err);
        toast({ title: "Warning", description: "Could not load score scale from server, using default.", variant: "destructive" });
      }
    };

    loadMaxScore();
  }, [loadModels]);

  // Reload models when the review tab becomes active
  useEffect(() => {
    if (activeTab === "review") {
      loadModels();
    }
  }, [activeTab, loadModels]);

  const handleFileSelect = useCallback((file: File) => {
    if (file.type === "application/pdf") {
      setSelectedFile(file);
      setResults(null);
    } else {
      toast({ title: "Invalid File", description: "Please select a PDF file", variant: "destructive" });
    }
  }, []);

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.[0]) {
        handleFileSelect(e.target.files[0]);
      }
    },
    [handleFileSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      if (e.dataTransfer.files?.[0]) {
        handleFileSelect(e.dataTransfer.files[0]);
      }
    },
    [handleFileSelect]
  );

  const startReview = async () => {
    if (!selectedFile) return;

    try {
      // Upload file
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(`${API_URL}/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to upload file");
      }

      const data = await response.json();
      const sessionId = data.session_id;
      const filename = selectedFile.name;

      // Show progress toast for this background review task
      const {
        id: toastId,
        update: updateToast,
        dismiss: dismissToast,
      } = toast({
        title: "Review in Progress",
        description: `Starting review of ${filename}...`,
        duration: Infinity,
      });

      // Connect WebSocket with optional model parameter
      const wsBaseUrl = getWebSocketUrl();
      const wsUrl = `${wsBaseUrl}/ws/session/${sessionId}${selectedModel ? `?model=${encodeURIComponent(selectedModel)}` : ""}`;
      const ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.status === "progress") {
          updateToast({
            id: toastId,
            title: "Review in Progress",
            description: `${filename}: ${message.progress}% — ${message.message}`,
            duration: Infinity,
          });
        } else if (message.status === "completed") {
          setResults(message.results);
          dismissToast();
          toast({
            title: "✅ Review Complete",
            description: `"${message.results.paper_title}" — ID: ${message.review_id ?? "N/A"}`,
          });
          ws.close();
        } else if (message.status === "error") {
          dismissToast();
          toast({
            title: "Review Failed",
            description: message.message,
            variant: "destructive",
          });
          ws.close();
        }
      };

      ws.onerror = () => {
        dismissToast();
        toast({
          title: "Connection Error",
          description: "Failed to connect to review service. Please try again.",
          variant: "destructive",
        });
      };
    } catch (err) {
      toast({
        title: "Upload Failed",
        description: err instanceof Error ? err.message : "An error occurred",
        variant: "destructive",
      });
    }
  };

  const getRecommendationColor = (recommendation: string) => {
    const rec = recommendation.toLowerCase();
    if (rec.includes("accept")) return "text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-950";
    if (rec.includes("reject")) return "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950";
    return "text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-950";
  };

  const handleReviewExpand = (reviewId: string | null) => {
    if (reviewId) {
      router.push(`/?tab=library&review=${encodeURIComponent(reviewId)}`);
    } else {
      router.push(`/?tab=library`);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
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

      {/* Main content */}
      <main className="flex-1 px-4 md:px-8 py-6 space-y-6">
        {activeTab === "review" && (
          <UploadArea
            selectedFile={selectedFile}
            selectedModel={selectedModel}
            availableModels={availableModels}
            onModelChange={setSelectedModel}
            fileInputRef={fileInputRef}
            isDragging={isDragging}
            handleDragOver={handleDragOver}
            handleDragLeave={handleDragLeave}
            handleDrop={handleDrop}
            handleFileInputChange={handleFileInputChange}
            startReview={startReview}
          />
        )}

        {activeTab === "library" && <ReviewLibrary initialExpandedReview={reviewParam} onReviewExpand={handleReviewExpand} />}

        {activeTab === "models" && <ModelManager />}

        {activeTab === "gpu" && <GpuMonitor />}

        {/* Results */}
        {results && <ResultsPanel results={results} getRecommendationColor={getRecommendationColor} maxScore={maxScore} />}
      </main>

      {/* Footer */}
      <footer className="border-t px-4 py-3 text-center">
        <p className="text-xs text-muted-foreground">Powered by local LLMs via Ollama • Privacy-first • Zero-cost</p>
      </footer>
    </div>
  );
}
