"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback } from "react";
import ReviewFormsBrowser from "@/features/forms/ReviewFormsBrowser";
import { useReview } from "@/features/review/review-context";

function FormsContent() {
  const router = useRouter();
  const { selectForm, isReviewing } = useReview();
  const selectedKey = useSearchParams().get("form");
  const onSelect = useCallback(
    (key: string | null) =>
      router.replace(key ? `/forms?form=${encodeURIComponent(key)}` : "/forms", { scroll: false }),
    [router],
  );
  const onUse = useCallback(
    (key: string) => {
      selectForm(key);
      router.push("/review");
    },
    [selectForm, router],
  );
  return <ReviewFormsBrowser selectedKey={selectedKey} onSelect={onSelect} onUse={isReviewing ? undefined : onUse} />;
}

export default function FormsPage() {
  // useSearchParams needs a Suspense boundary so the rest of the page can be prerendered.
  return (
    <Suspense fallback={null}>
      <FormsContent />
    </Suspense>
  );
}
