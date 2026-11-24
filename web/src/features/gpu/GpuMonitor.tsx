"use client";

import { useQuery } from "@tanstack/react-query";
import { Cpu, RefreshCw } from "lucide-react";
import { useState } from "react";
import { ErrorAlert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { queries } from "@/lib/api/queries";
import GpuCard from "./GpuCard";

const REFRESH_MS = 2000;

export default function GpuMonitor() {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  // The only place that polls the GPUs, and only while this page is open and the browser tab is visible.
  const { data, error, refetch } = useQuery({
    ...queries.gpus(),
    refetchOnMount: "always",
    refetchInterval: autoRefresh ? REFRESH_MS : false,
  });

  const gpus = data?.gpus ?? [];
  const displayedGpus = selectedIndex !== null ? gpus.filter((g) => g.index === selectedIndex) : gpus;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle>🖥️ GPU Monitor</CardTitle>
            <CardDescription>Real-time GPU utilization and memory usage</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {data && data.count > 1 && (
              <NativeSelect
                aria-label="GPU"
                value={selectedIndex ?? "all"}
                onChange={(e) => setSelectedIndex(e.target.value === "all" ? null : Number(e.target.value))}
                className="w-auto py-1"
              >
                <option value="all">All GPUs</option>
                {data.gpus.map((g) => (
                  <option key={g.index} value={g.index}>
                    GPU {g.index}: {g.name}
                  </option>
                ))}
              </NativeSelect>
            )}
            <Button
              size="sm"
              variant={autoRefresh ? "default" : "outline"}
              onClick={() => setAutoRefresh((v) => !v)}
              title={autoRefresh ? "Pause auto-refresh" : "Resume auto-refresh"}
            >
              <RefreshCw className={`h-4 w-4 ${autoRefresh ? "animate-spin" : ""}`} />
              <span className="ml-1 hidden sm:inline">{autoRefresh ? "Live" : "Paused"}</span>
            </Button>
            {!autoRefresh && (
              <Button size="sm" variant="outline" onClick={() => refetch()}>
                Refresh
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ErrorAlert className="mb-4">{error && (error.message || "Failed to fetch GPU data")}</ErrorAlert>

        {data && !data.available && (
          <div className="py-12 text-center text-muted-foreground">
            <Cpu className="mx-auto mb-3 h-12 w-12 opacity-30" />
            <p className="text-sm">No NVIDIA GPU detected.</p>
            <p className="mt-1 text-xs">GPU monitoring requires an NVIDIA GPU with the NVML driver library.</p>
          </div>
        )}

        {data?.available && displayedGpus.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">No GPUs found.</p>
        )}

        <div className="space-y-4">
          {displayedGpus.map((gpu) => (
            <GpuCard key={gpu.index} gpu={gpu} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
