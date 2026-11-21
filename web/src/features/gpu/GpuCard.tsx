import { Cpu } from "lucide-react";
import UsageBar from "@/components/UsageBar";
import { formatBytes } from "@/lib/format";
import type { GpuStats } from "@/lib/types";

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
}

export default function GpuCard({ gpu }: { gpu: GpuStats }) {
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
        <UsageBar value={gpu.gpu_utilization} color="bg-blue-500" />
      </div>

      {/* Memory utilization */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Memory</span>
          <span>
            {formatBytes(gpu.memory_used)} / {formatBytes(gpu.memory_total)} ({memPct.toFixed(1)}%)
          </span>
        </div>
        <UsageBar value={memPct} color="bg-green-500" />
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
