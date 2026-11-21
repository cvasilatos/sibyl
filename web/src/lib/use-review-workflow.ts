"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";
import { fetchMaxScore, getWebSocketUrl } from "@/lib/config";
import type { AppTab, ConferenceSummary, GpuStats, ReviewResults } from "@/lib/types";

interface ReviewSocketMessage {
  status: "progress" | "completed" | "error";
  progress?: number;
  message?: string;
  review_id?: string;
  results?: ReviewResults;
}

export function useReviewWorkflow(activeTab: AppTab) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedReviewForm, setSelectedReviewForm] = useState<File | null>(null);
  const [conferences, setConferences] = useState<ConferenceSummary[]>([]);
  const [selectedConferenceId, setSelectedConferenceId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [availableGpus, setAvailableGpus] = useState<Array<Pick<GpuStats, "index" | "name">>>([]);
  const [selectedGpuIndex, setSelectedGpuIndex] = useState<number | null>(null);
  const [results, setResults] = useState<ReviewResults | null>(null);
  const [isReviewing, setIsReviewing] = useState(false);
  const [maxScore, setMaxScore] = useState(10);
  const selectedGpuIndexRef = useRef<number | null>(null);
  const activeSocketRef = useRef<WebSocket | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const reviewFormInputRef = useRef<HTMLInputElement>(null);

  selectedGpuIndexRef.current = selectedGpuIndex;

  const loadModels = useCallback(async () => {
    try {
      const data = await api.listInstalledModels();
      const modelNames = data.models.map((model) => model.model);
      setAvailableModels(modelNames);
      setSelectedModel((current) => (current && modelNames.includes(current) ? current : (modelNames[0] ?? "")));
    } catch (error) {
      console.error("Failed to load models:", error);
    }
  }, []);

  const loadGpus = useCallback(async () => {
    try {
      const data = await api.listGpus();
      if (!data.available) {
        setAvailableGpus([]);
        setSelectedGpuIndex(null);
        return;
      }

      const gpuList = data.gpus ?? [];
      setAvailableGpus(gpuList);
      if (gpuList.length === 0) {
        setSelectedGpuIndex(null);
      } else if (selectedGpuIndexRef.current !== null && !gpuList.some((gpu) => gpu.index === selectedGpuIndexRef.current)) {
        setSelectedGpuIndex(gpuList[0].index);
      }
    } catch (error) {
      console.error("Failed to load GPUs:", error);
      setAvailableGpus([]);
      setSelectedGpuIndex(null);
    }
  }, []);

  useEffect(() => {
    loadModels();
    loadGpus();
    api
      .listConferences()
      .then((data) => setConferences(data.conferences))
      .catch((error) => console.error("Failed to load conference templates:", error));
    fetchMaxScore()
      .then(setMaxScore)
      .catch((error) => {
        console.error("Failed to load max score:", error);
        toast({ title: "Warning", description: "Could not load score scale from server, using default.", variant: "destructive" });
      });
  }, [loadGpus, loadModels]);

  useEffect(() => {
    if (activeTab === "review") loadModels();
  }, [activeTab, loadModels]);

  useEffect(
    () => () => {
      const socket = activeSocketRef.current;
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    },
    []
  );

  const selectFile = useCallback((file: File) => {
    if (file.type !== "application/pdf") {
      toast({ title: "Invalid File", description: "Please select a PDF file", variant: "destructive" });
      return;
    }
    setSelectedFile(file);
    setResults(null);
  }, []);

  const selectReviewForm = useCallback((file: File | null) => {
    if (file === null) {
      setSelectedReviewForm(null);
      if (reviewFormInputRef.current) reviewFormInputRef.current.value = "";
      return;
    }

    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (![".txt", ".md", ".markdown"].includes(extension)) {
      toast({ title: "Invalid Review Form", description: "Choose a .txt, .md, or .markdown file.", variant: "destructive" });
      return;
    }
    if (file.size > 64 * 1024) {
      toast({ title: "Review Form Too Large", description: "The review form must be 64 KiB or smaller.", variant: "destructive" });
      return;
    }
    setSelectedReviewForm(file);
    setSelectedConferenceId(null);
    setResults(null);
  }, []);

  const selectConference = useCallback((conferenceId: string | null) => {
    setSelectedConferenceId(conferenceId);
    if (conferenceId) {
      setSelectedReviewForm(null);
      if (reviewFormInputRef.current) reviewFormInputRef.current.value = "";
    }
    setResults(null);
  }, []);

  const startReview = useCallback(
    async (gpuIndex: number | null) => {
      if (!selectedFile || !selectedModel) {
        toast({ title: "Cannot Start Review", description: "Select a PDF and an installed model first.", variant: "destructive" });
        return;
      }

      setIsReviewing(true);
      try {
        const upload = await api.uploadPaper(selectedFile, selectedReviewForm, selectedConferenceId);
        const hostIndex = gpuIndex !== null ? gpuIndex + 1 : 0;
        const filename = selectedFile.name;
        const progressToast = toast({
          title: "Review in Progress",
          description: `Starting review of ${filename}...`,
          duration: Infinity,
        });
        const params = new URLSearchParams({ model: selectedModel, host: String(hostIndex) });
        const socket = new WebSocket(`${getWebSocketUrl()}/ws/session/${upload.session_id}?${params}`);
        activeSocketRef.current = socket;
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
              description: `${filename}: ${message.progress ?? 0}% — ${message.message ?? "Working..."}`,
              duration: Infinity,
            });
          } else if (message.status === "completed" && message.results) {
            finished = true;
            setIsReviewing(false);
            setResults(message.results);
            progressToast.dismiss();
            toast({ title: "✅ Review Complete", description: `"${message.results.paper_title}" — ID: ${message.review_id ?? "N/A"}` });
            socket.close();
          } else if (message.status === "error") {
            fail(message.message ?? "The review failed.");
            socket.close();
          }
        };
        socket.onerror = () => fail("Failed to connect to review service. Please try again.");
        socket.onclose = () => {
          activeSocketRef.current = null;
          if (!finished) fail("The review connection closed unexpectedly.");
        };
      } catch (error) {
        setIsReviewing(false);
        toast({ title: "Upload Failed", description: error instanceof Error ? error.message : "An error occurred", variant: "destructive" });
      }
    },
    [selectedFile, selectedModel, selectedReviewForm, selectedConferenceId]
  );

  return {
    selectedFile,
    selectFile,
    selectedReviewForm,
    selectReviewForm,
    conferences,
    selectedConferenceId,
    selectConference,
    selectedModel,
    setSelectedModel,
    availableModels,
    availableGpus,
    selectedGpuIndex,
    setSelectedGpuIndex,
    results,
    isReviewing,
    maxScore,
    fileInputRef,
    reviewFormInputRef,
    startReview,
  };
}
