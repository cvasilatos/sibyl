import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export function Spinner({ className, label = "Loading" }: { className?: string; label?: string }) {
  return <Loader2 className={cn("h-4 w-4 animate-spin", className)} aria-label={label} role="status" />;
}

/** A spinner centered in a padded block, for whole sections that are loading. */
export function LoadingBlock({ className, label }: { className?: string; label?: string }) {
  return (
    <div className={cn("flex items-center justify-center py-8", className)}>
      <Spinner className="h-6 w-6 text-muted-foreground" label={label} />
    </div>
  );
}
