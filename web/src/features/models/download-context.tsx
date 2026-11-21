"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";
import { toast } from "@/hooks/use-toast";
import { invalidates } from "@/lib/api/queries";
import { getWebSocketUrl } from "@/lib/config";

/** A message on the model pull WebSocket: the engine's progress lines, then "success" or "error". */
interface PullMessage {
  status: string;
  message?: string;
  total?: number;
  completed?: number;
}

interface DownloadContextType {
  /** Models being installed, by full name (name:tag). */
  installing: string[];
  downloadProgresses: Record<string, number>;
  /** The last failure, until the next download starts or clearError is called. */
  error: string | null;
  startDownload: (modelName: string) => void;
  clearError: () => void;
}

const DownloadContext = createContext<DownloadContextType | undefined>(undefined);

/** Model installs, streamed over WebSockets. Lives in the root layout so downloads continue across pages. */
export function DownloadProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [installing, setInstalling] = useState<string[]>([]);
  const [downloadProgresses, setDownloadProgresses] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const startDownload = useCallback(
    (modelName: string) => {
      setInstalling((prev) => [...prev, modelName]);
      setDownloadProgresses((prev) => ({ ...prev, [modelName]: 0 }));
      setError(null);
      const progressToast = toast({ title: "Downloading Model", description: `Installing ${modelName}...` });

      let finished = false;
      const finish = (failure?: string) => {
        if (finished) return;
        finished = true;
        setInstalling((prev) => prev.filter((m) => m !== modelName));
        setDownloadProgresses(({ [modelName]: _, ...rest }) => rest);
        progressToast.dismiss();
        if (failure) {
          setError(failure);
          toast({ title: "Installation Failed", description: failure, variant: "destructive" });
        } else {
          toast({ title: "Installation Complete", description: `${modelName} has been successfully installed!` });
        }
        queryClient.invalidateQueries(invalidates.models);
      };

      let ws: WebSocket;
      try {
        ws = new WebSocket(`${getWebSocketUrl()}/ws/pull?model_name=${encodeURIComponent(modelName)}`);
      } catch (err) {
        finish(err instanceof Error ? err.message : "Failed to start model installation");
        return;
      }
      let progress = 0;

      ws.onmessage = (event) => {
        let data: PullMessage;
        try {
          data = JSON.parse(event.data) as PullMessage;
        } catch (e) {
          console.error("Error parsing pull message:", e);
          return;
        }
        if (data.status === "error") {
          finish(data.message ?? "Installation failed");
          ws.close();
          return;
        }
        if (data.total && data.completed) {
          progress = Math.round((data.completed / data.total) * 100);
          setDownloadProgresses((prev) => ({ ...prev, [modelName]: progress }));
        }
        progressToast.update({ id: progressToast.id, title: "Downloading Model", description: `${modelName}: ${progress}% - ${data.status}` });
        if (data.status === "success") {
          finish();
          ws.close();
        }
      };
      ws.onerror = () => finish("Failed to connect to download stream");
      ws.onclose = () => finish("Connection lost during model download");
    },
    [queryClient]
  );

  const value = useMemo(() => ({ installing, downloadProgresses, error, startDownload, clearError }), [installing, downloadProgresses, error, startDownload, clearError]);

  return <DownloadContext.Provider value={value}>{children}</DownloadContext.Provider>;
}

export function useDownload() {
  const context = useContext(DownloadContext);
  if (context === undefined) {
    throw new Error("useDownload must be used within a DownloadProvider");
  }
  return context;
}
