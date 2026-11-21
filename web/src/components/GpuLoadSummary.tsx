"use client";

import { useCallback, useEffect, useState } from "react";
import UsageBar from "@/components/UsageBar";
import { api } from "@/lib/api";
import type { GpuSummary } from "@/lib/types";

export default function GpuLoadSummary() {
  const [gpus, setGpus] = useState<GpuSummary[]>([]);

  const fetchGpus = useCallback(async () => {
    try {
      const data = await api.listGpus();
      if (data.available) setGpus(data.gpus ?? []);
    } catch {
      // Supplementary info – silently ignore errors
    }
  }, []);

  useEffect(() => {
    fetchGpus();
    const interval = setInterval(fetchGpus, 3000);
    return () => clearInterval(interval);
  }, [fetchGpus]);

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
