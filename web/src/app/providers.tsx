"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import AuthGate from "@/features/auth/AuthGate";
import { DownloadProvider } from "@/features/models/download-context";
import { ReviewProvider } from "@/features/review/review-context";
import { createQueryClient } from "@/lib/api/queries";

/** App-wide client state. Providers here outlive page changes. Nothing but the sign-in page renders until signed in. */
export default function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);
  return (
    <QueryClientProvider client={queryClient}>
      <AuthGate>
        <DownloadProvider>
          <ReviewProvider>{children}</ReviewProvider>
        </DownloadProvider>
      </AuthGate>
    </QueryClientProvider>
  );
}
