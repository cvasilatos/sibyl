"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import SearchInput from "@/components/SearchInput";
import { ErrorAlert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingBlock, Spinner } from "@/components/ui/spinner";
import { canManage, useCurrentUser } from "@/hooks/use-current-user";
import { useMaxScore } from "@/hooks/use-max-score";
import { api } from "@/lib/api";
import { invalidates, queries } from "@/lib/api/queries";
import type { StoredReview } from "@/lib/types";
import LibraryStats from "./LibraryStats";
import PaperReviewsDialog from "./PaperReviewsDialog";
import ReviewListItem from "./ReviewListItem";

function matches(review: StoredReview, query: string): boolean {
  return [
    review.paper_title,
    review.pdf_filename,
    review.reviewer_model,
    review.recommendation,
    review.review_summary,
    review.owner ?? "",
  ].some((field) => field.toLowerCase().includes(query));
}

type Props = {
  /** The review shown in full, or null. Controlled by the page so it can live in the URL. */
  expandedReviewId: string | null;
  onExpandedChange: (reviewId: string | null) => void;
};

export default function ReviewLibrary({ expandedReviewId, onExpandedChange }: Props) {
  const queryClient = useQueryClient();
  const maxScore = useMaxScore();
  const user = useCurrentUser();
  const reviews = useQuery(queries.reviews());
  const stats = useQuery(queries.statistics());
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPaperTitle, setSelectedPaperTitle] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = () => queryClient.invalidateQueries(invalidates.reviews);
  const deleteReview = useMutation({
    mutationFn: api.deleteReview,
    onMutate: () => setActionError(null),
    onSuccess: (_, reviewId) => {
      if (reviewId === expandedReviewId) onExpandedChange(null);
      return refresh();
    },
    onError: (err) => setActionError(err.message || "Failed to delete review"),
  });
  const deleteAll = useMutation({
    mutationFn: api.deleteAllReviews,
    onMutate: () => setActionError(null),
    onSuccess: () => {
      onExpandedChange(null);
      return refresh();
    },
    onError: (err) => setActionError(err.message || "Failed to delete all reviews"),
  });

  const allReviews = reviews.data ?? [];
  // Everyone sees every review, but deletes only their own (admins delete any, and "Delete All" deletes everything).
  const deletable = allReviews.filter((review) => canManage(user, review.owner));
  const deleteAllLabel = user?.is_admin ? "Delete All" : "Delete All Mine";
  const filteredReviews = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return query ? (reviews.data ?? []).filter((review) => matches(review, query)) : (reviews.data ?? []);
  }, [reviews.data, searchQuery]);
  const loadError = reviews.error ?? stats.error;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>📚 Review Library</CardTitle>
            <CardDescription>
              Everyone&apos;s reviews; you can delete {user?.is_admin ? "any of them" : "the ones you ran"}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={() =>
                confirm(
                  user?.is_admin
                    ? "Are you sure you want to delete ALL reviews, everyone's? This cannot be undone."
                    : `Are you sure you want to delete all ${deletable.length} of your reviews? This cannot be undone.`,
                ) && deleteAll.mutate()
              }
              disabled={deleteAll.isPending || reviews.isPending || deletable.length === 0}
              size="sm"
              variant="destructive"
            >
              {deleteAll.isPending ? <Spinner label="Deleting" /> : <Trash2 className="h-4 w-4" />}
              {deleteAllLabel}
            </Button>
            <Button
              onClick={refresh}
              disabled={reviews.isFetching}
              size="sm"
              variant="outline"
              aria-label="Refresh reviews"
            >
              <RefreshCw className={`h-4 w-4 ${reviews.isFetching ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ErrorAlert>{actionError ?? (loadError && (loadError.message || "Failed to load reviews"))}</ErrorAlert>
        {stats.data && <LibraryStats stats={stats.data} />}
        <SearchInput
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder="Search reviews by title, model, recommendation…"
        />

        <div className="space-y-2">
          {reviews.isPending ? (
            <LoadingBlock />
          ) : filteredReviews.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {searchQuery.trim() ? "No reviews match your search." : "No reviews yet. Upload a paper to get started!"}
            </p>
          ) : (
            filteredReviews.map((review) => (
              <ReviewListItem
                key={review.id}
                review={review}
                maxScore={maxScore}
                expanded={expandedReviewId === review.id}
                onToggle={() => onExpandedChange(expandedReviewId === review.id ? null : review.id)}
                onShowPaper={() => setSelectedPaperTitle(review.paper_title)}
                onDelete={
                  canManage(user, review.owner)
                    ? () => confirm("Are you sure you want to delete this review?") && deleteReview.mutate(review.id)
                    : undefined
                }
                deleting={deleteReview.isPending && deleteReview.variables === review.id}
                onError={setActionError}
              />
            ))
          )}
        </div>
      </CardContent>

      <PaperReviewsDialog
        paperTitle={selectedPaperTitle}
        reviews={allReviews}
        maxScore={maxScore}
        onClose={() => setSelectedPaperTitle(null)}
      />
    </Card>
  );
}
