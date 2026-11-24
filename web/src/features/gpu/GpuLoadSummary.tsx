"use client";

import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import UsageBar from "@/components/UsageBar";
import { Button } from "@/components/ui/button";
import { queries } from "@/lib/api/queries";

/** Load of each GPU, shown under the review form. Read once and refreshed on demand: the GPU page is the live view. */
export default function GpuLoadSummary() {
  // Supplementary info: errors just hide the summary.
  const { data, dataUpdatedAt, isFetching, refetch } = useQuery(queries.gpus());
  const gpus = data?.available ? data.gpus : [];

  if (gpus.length === 0) return null;

  return (
    <div className="p-3 border rounded-md bg-muted/30 space-y-2">
      <div className="flex items-center gap-2">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">GPU Load</p>
        <span className="text-xs text-muted-foreground ml-auto">
          as of {new Date(dataUpdatedAt).toLocaleTimeString()}
        </span>
        <Button
          size="sm"
          variant="ghost"
          className="h-6 px-2"
          onClick={() => refetch()}
          disabled={isFetching}
          title="Read the current GPU load"
        >
          <RefreshCw className={`h-3 w-3 ${isFetching ? "animate-spin" : ""}`} />
          <span className="ml-1">Refresh</span>
        </Button>
      </div>
      {gpus.map((gpu) => {
        const memPct = gpu.memory_total > 0 ? (gpu.memory_used / gpu.memory_total) * 100 : 0;
        return (
          <div key={gpu.index} className="space-y-1">
            <p className="text-xs text-muted-foreground truncate">
              GPU {gpu.index}: {gpu.name}
            </p>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground w-8 shrink-0">Core</span>
              <UsageBar size="sm" value={gpu.gpu_utilization} color="bg-blue-500" />
              <span className="text-xs font-mono w-8 text-right shrink-0">{gpu.gpu_utilization}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground w-8 shrink-0">VRAM</span>
              <UsageBar size="sm" value={memPct} color="bg-green-500" />
              <span className="text-xs font-mono w-8 text-right shrink-0">{memPct.toFixed(0)}%</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
