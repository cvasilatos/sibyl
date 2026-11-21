"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback } from "react";
import ReviewLibrary from "@/features/library/ReviewLibrary";

function LibraryContent() {
  const router = useRouter();
  const expandedReview = useSearchParams().get("review");
  const onReviewExpand = useCallback(
    (reviewId: string | null) => router.replace(reviewId ? `/library?review=${encodeURIComponent(reviewId)}` : "/library", { scroll: false }),
    [router]
  );
  return <ReviewLibrary initialExpandedReview={expandedReview} onReviewExpand={onReviewExpand} />;
}

export default function LibraryPage() {
  // useSearchParams needs a Suspense boundary so the rest of the page can be prerendered.
  return (
    <Suspense fallback={null}>
      <LibraryContent />
    </Suspense>
  );
}
