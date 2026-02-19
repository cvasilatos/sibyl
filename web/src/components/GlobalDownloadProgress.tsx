"use client"

import { useDownload } from "@/lib/download-context"
import { Progress } from "@/components/ui/progress"

export function GlobalDownloadProgress() {
  const { installing, downloadProgress } = useDownload()

  if (!installing) return null

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-background border-b p-4 shadow-md">
      <div className="max-w-4xl mx-auto space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span>Installing {installing}...</span>
          <span>{downloadProgress}%</span>
        </div>
        <Progress value={downloadProgress} />
      </div>
    </div>
  )
}