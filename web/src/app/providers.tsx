"use client";

import type { ReactNode } from "react";
import { DownloadProvider } from "@/features/models/download-context";
import { ReviewProvider } from "@/features/review/review-context";

/** App-wide client state. Providers here outlive page changes. */
export default function Providers({ children }: { children: ReactNode }) {
  return (
    <DownloadProvider>
      <ReviewProvider>{children}</ReviewProvider>
    </DownloadProvider>
  );
}
