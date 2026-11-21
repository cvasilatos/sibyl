"use client";

import { Cpu, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatBytes } from "@/lib/presentation";
import type { GpuResponse, GpuStats } from "@/lib/types";

function UtilBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="w-full bg-muted rounded-full h-3 overflow-hidden">
      <div className={`h-3 rounded-full transition-all duration-500 ${color}`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
}

function GpuCard({ gpu }: { gpu: GpuStats }) {
  const memPct = gpu.memory_total > 0 ? (gpu.memory_used / gpu.memory_total) * 100 : 0;

  return (
    <div className="space-y-4 p-4 bg-muted/40 rounded-lg border">
      <div className="flex items-center gap-2">
        <Cpu className="h-4 w-4 text-muted-foreground" />
        <span className="font-medium text-sm">{gpu.name}</span>
        <span className="text-xs text-muted-foreground ml-auto">GPU {gpu.index}</span>
      </div>

      {/* GPU utilization */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>GPU Load</span>
          <span>{gpu.gpu_utilization}%</span>
        </div>
        <UtilBar value={gpu.gpu_utilization} color="bg-blue-500" />
      </div>

      {/* Memory utilization */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Memory</span>
          <span>
            {formatBytes(gpu.memory_used)} / {formatBytes(gpu.memory_total)} ({memPct.toFixed(1)}%)
          </span>
        </div>
        <UtilBar value={memPct} color="bg-green-500" />
      </div>

      {/* Detailed stats grid */}
      <div className="space-y-1 pt-1 border-t border-border">
        {gpu.temperature !== null && <StatRow label="Temperature" value={`${gpu.temperature} °C`} />}
        {gpu.power_usage_watts !== null && gpu.power_limit_watts !== null && (
          <StatRow label="Power" value={`${gpu.power_usage_watts.toFixed(0)} W / ${gpu.power_limit_watts.toFixed(0)} W`} />
        )}
        {gpu.fan_speed_percent !== null && <StatRow label="Fan Speed" value={`${gpu.fan_speed_percent}%`} />}
        <StatRow label="Free Memory" value={formatBytes(gpu.memory_free)} />
      </div>

      {/* Running processes */}
      {gpu.processes && gpu.processes.length > 0 && (
        <div className="space-y-1 pt-1 border-t border-border">
          <p className="text-xs font-medium text-muted-foreground">Processes ({gpu.processes.length})</p>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {gpu.processes.map((p, i) => (
              <div key={`${p.type}-${p.pid}-${i}`} className="flex items-center justify-between text-xs gap-2">
                <span className="font-mono truncate flex-1">{p.name || `PID ${p.pid}`}</span>
                <span
                  className={`shrink-0 px-1 rounded ${p.type === "compute" ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300" : "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300"}`}
                >
                  {p.type}
                </span>
                <span className="font-mono shrink-0">{formatBytes(p.memory_bytes)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function GpuMonitor() {
  const [data, setData] = useState<GpuResponse | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchGpus = useCallback(async () => {
    try {
      const result = await api.listGpus();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch GPU data");
    }
  }, []);

  // Initial fetch + auto-refresh every 2 seconds
  useEffect(() => {
    fetchGpus();
    if (!autoRefresh) return;
    const interval = setInterval(fetchGpus, 2000);
    return () => clearInterval(interval);
  }, [fetchGpus, autoRefresh]);

  const displayedGpus = selectedIndex !== null ? (data?.gpus.filter((g) => g.index === selectedIndex) ?? []) : (data?.gpus ?? []);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle>🖥️ GPU Monitor</CardTitle>
            <CardDescription>Real-time GPU utilization and memory usage</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {/* GPU selector */}
            {data && data.count > 1 && (
              <select
                value={selectedIndex ?? "all"}
                onChange={(e) => setSelectedIndex(e.target.value === "all" ? null : Number(e.target.value))}
                className="text-sm border border-input rounded-md px-2 py-1 bg-background"
              >
                <option value="all">All GPUs</option>
                {data.gpus.map((g) => (
                  <option key={g.index} value={g.index}>
                    GPU {g.index}: {g.name}
                  </option>
                ))}
              </select>
            )}
            {/* Auto-refresh toggle */}
            <Button
              size="sm"
              variant={autoRefresh ? "default" : "outline"}
              onClick={() => setAutoRefresh((v) => !v)}
              title={autoRefresh ? "Pause auto-refresh" : "Resume auto-refresh"}
            >
              <RefreshCw className={`h-4 w-4 ${autoRefresh ? "animate-spin" : ""}`} />
              <span className="ml-1 hidden sm:inline">{autoRefresh ? "Live" : "Paused"}</span>
            </Button>
            {/* Manual refresh */}
            {!autoRefresh && (
              <Button size="sm" variant="outline" onClick={fetchGpus}>
                Refresh
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="p-3 bg-destructive/10 border border-destructive rounded-md mb-4">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {data && !data.available && (
          <div className="text-center py-12 text-muted-foreground">
            <Cpu className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No NVIDIA GPU detected.</p>
            <p className="text-xs mt-1">GPU monitoring requires an NVIDIA GPU with the NVML driver library.</p>
          </div>
        )}

        {data?.available && displayedGpus.length === 0 && <p className="text-sm text-muted-foreground text-center py-8">No GPUs found.</p>}

        <div className="space-y-4">
          {displayedGpus.map((gpu) => (
            <GpuCard key={gpu.index} gpu={gpu} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
