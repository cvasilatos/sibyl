import { cn } from "@/lib/utils";

/**
 * A horizontal bar filled to `value` percent (clamped to 0–100).
 * Decorative: callers print the number next to it, so it is hidden from screen readers.
 */
export default function UsageBar({ value, color, size = "md" }: { value: number; color: string; size?: "sm" | "md" }) {
  const height = size === "sm" ? "h-1.5" : "h-3";
  return (
    <div className={cn("w-full flex-1 overflow-hidden rounded-full bg-muted", height)} aria-hidden="true">
      <div
        className={cn("rounded-full transition-all duration-500", height, color)}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
