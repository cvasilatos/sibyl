"use client";

import { Progress } from "@/components/ui/progress";
import { useDownload } from "@/features/models/download-context";

export function GlobalDownloadProgress() {
  const { installing, downloadProgresses } = useDownload();

  if (installing.length === 0) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 right-4 z-50 w-72 max-w-[calc(100vw-2rem)] rounded-lg border bg-background p-3 shadow-lg"
    >
      <div className="space-y-3">
        {installing.map((modelName) => (
          <div key={modelName} className="space-y-1">
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="truncate" title={modelName}>
                Installing {modelName}...
              </span>
              <span className="shrink-0 tabular-nums">{downloadProgresses[modelName] || 0}%</span>
            </div>
            <Progress value={downloadProgresses[modelName] || 0} />
          </div>
        ))}
      </div>
    </div>
  );
}
