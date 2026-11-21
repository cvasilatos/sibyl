"use client";

import { Progress } from "@/components/ui/progress";
import { useDownload } from "@/features/models/download-context";

export function GlobalDownloadProgress() {
  const { installing, downloadProgresses } = useDownload();

  if (installing.length === 0) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-background border-b p-4 shadow-md">
      <div className="max-w-4xl mx-auto space-y-3">
        {installing.map((modelName) => (
          <div key={modelName} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span>Installing {modelName}...</span>
              <span>{downloadProgresses[modelName] || 0}%</span>
            </div>
            <Progress value={downloadProgresses[modelName] || 0} />
          </div>
        ))}
      </div>
    </div>
  );
}
