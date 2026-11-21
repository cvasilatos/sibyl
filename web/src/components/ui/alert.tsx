import type * as React from "react";

import { cn } from "@/lib/utils";

/** A destructive message box. Renders nothing without children, so `<ErrorAlert>{error}</ErrorAlert>` is safe when `error` is null. */
export function ErrorAlert({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  if (children === null || children === undefined || children === false || children === "") return null;
  return (
    <div role="alert" className={cn("rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive", className)} {...props}>
      {children}
    </div>
  );
}
