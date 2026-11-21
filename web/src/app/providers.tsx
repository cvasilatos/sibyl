"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { DownloadProvider } from "@/features/models/download-context";
import { ReviewProvider } from "@/features/review/review-context";
import { createQueryClient } from "@/lib/api/queries";

/** App-wide client state. Providers here outlive page changes. */
export default function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);
  return (
    <QueryClientProvider client={queryClient}>
      <DownloadProvider>
        <ReviewProvider>{children}</ReviewProvider>
      </DownloadProvider>
    </QueryClientProvider>
  );
}
