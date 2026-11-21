"use client";

import { useQuery } from "@tanstack/react-query";
import UsageBar from "@/components/UsageBar";
import { queries } from "@/lib/api/queries";

/** Compact live load of each GPU, shown under the review form. */
export default function GpuLoadSummary() {
  // Supplementary info: errors just hide the summary.
  const { data } = useQuery({ ...queries.gpus(), refetchInterval: 3000 });
  const gpus = data?.available ? data.gpus : [];

  if (gpus.length === 0) return null;

  return (
    <div className="p-3 border rounded-md bg-muted/30 space-y-2">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">GPU Load</p>
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
