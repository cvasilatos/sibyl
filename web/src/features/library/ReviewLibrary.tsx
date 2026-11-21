"use client";

import { ChevronDown, ChevronUp, Download, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import RecommendationBadge from "@/components/RecommendationBadge";
import ReviewDetails from "@/components/ReviewDetails";
import SearchInput from "@/components/SearchInput";
import { ErrorAlert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { LoadingBlock, Spinner } from "@/components/ui/spinner";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { saveBlob } from "@/lib/download";
import { formatDate } from "@/lib/format";
import type { FullReview, ReviewStatistics, StoredReview } from "@/lib/types";

export default function ReviewLibrary({
  initialExpandedReview = null,
  onReviewExpand,
}: {
  initialExpandedReview?: string | null;
  onReviewExpand?: (reviewId: string | null) => void;
}) {
  const [reviews, setReviews] = useState<StoredReview[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [deletingAll, setDeletingAll] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<ReviewStatistics | null>(null);
  const [expandedReview, setExpandedReview] = useState<string | null>(initialExpandedReview);
  const [fullReviewData, setFullReviewData] = useState<Record<string, FullReview>>({});
  const [loadingFull, setLoadingFull] = useState<string | null>(null);
  const [maxScore, setMaxScore] = useState<number>(10);
  const [selectedPaperTitle, setSelectedPaperTitle] = useState<string | null>(null);

  const filteredReviews = useMemo(() => {
    if (!searchQuery.trim()) return reviews;
    const q = searchQuery.toLowerCase();
    return reviews.filter(
      (r) =>
        r.paper_title.toLowerCase().includes(q) ||
        r.pdf_filename.toLowerCase().includes(q) ||
        r.reviewer_model.toLowerCase().includes(q) ||
        r.recommendation.toLowerCase().includes(q) ||
        r.review_summary.toLowerCase().includes(q)
    );
  }, [reviews, searchQuery]);

  const loadReviews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [reviewsData, statsData] = await Promise.all([api.listReviews(), api.getStatistics()]);

      setReviews(reviewsData.reviews);
      setStats(statsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reviews");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReviews();
    api
      .getMaxScore()
      .then(setMaxScore)
      .catch((err) => {
        console.error("Failed to load max score:", err);
        toast({ title: "Warning", description: "Could not load score scale from server, using default.", variant: "destructive" });
      });
  }, [loadReviews]);

  // Follow the URL when it changes (back/forward, or a link to a review).
  useEffect(() => setExpandedReview(initialExpandedReview), [initialExpandedReview]);

  // Load the full review the first time it is expanded.
  useEffect(() => {
    if (!expandedReview || fullReviewData[expandedReview]) return;
    const reviewId = expandedReview;
    const controller = new AbortController();
    setLoadingFull(reviewId);
    api
      .getReview(reviewId, controller.signal)
      .then((data) => setFullReviewData((prev) => ({ ...prev, [reviewId]: data })))
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Failed to load review details");
        setExpandedReview(null);
      })
      .finally(() => setLoadingFull((current) => (current === reviewId ? null : current)));
    return () => controller.abort();
  }, [expandedReview, fullReviewData]);

  const deleteReview = async (reviewId: string) => {
    if (!confirm("Are you sure you want to delete this review?")) {
      return;
    }

    setDeleting(reviewId);
    setError(null);
    try {
      await api.deleteReview(reviewId);
      await loadReviews();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete review");
    } finally {
      setDeleting(null);
    }
  };

  const deleteAllReviews = async () => {
    if (!confirm("Are you sure you want to delete ALL reviews? This cannot be undone.")) {
      return;
    }

    setDeletingAll(true);
    setError(null);
    try {
      await api.deleteAllReviews();
      await loadReviews();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete all reviews");
    } finally {
      setDeletingAll(false);
    }
  };

  const downloadPDF = async (reviewId: string, filename: string) => {
    setDownloading(reviewId);
    setError(null);
    try {
      saveBlob(await api.downloadReviewPdf(reviewId), filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download PDF");
    } finally {
      setDownloading(null);
    }
  };

  const toggleExpand = (reviewId: string) => {
    const next = expandedReview === reviewId ? null : reviewId;
    setExpandedReview(next);
    onReviewExpand?.(next);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>📚 Review Library</CardTitle>
            <CardDescription>Browse and manage your saved reviews</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={deleteAllReviews} disabled={deletingAll || loading || reviews.length === 0} size="sm" variant="destructive">
              {deletingAll ? <Spinner label="Deleting" /> : <Trash2 className="h-4 w-4" />}
              Delete All
            </Button>
            <Button onClick={loadReviews} disabled={loading} size="sm" variant="outline" aria-label="Refresh reviews">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ErrorAlert>{error}</ErrorAlert>

        {/* Statistics */}
        {stats && (
          <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-md">
            <div className="text-center">
              <p className="text-2xl font-bold text-primary">{stats.total_reviews}</p>
              <p className="text-xs text-muted-foreground">Total Reviews</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-primary">{stats.unique_papers}</p>
              <p className="text-xs text-muted-foreground">Unique Papers</p>
            </div>
          </div>
        )}

        {/* Search input */}
        <SearchInput value={searchQuery} onChange={setSearchQuery} placeholder="Search reviews by title, model, recommendation…" />

        {/* Reviews list */}
        <div className="space-y-2">
          {loading ? (
            <LoadingBlock />
          ) : filteredReviews.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              {searchQuery.trim() ? "No reviews match your search." : "No reviews yet. Upload a paper to get started!"}
            </p>
          ) : (
            filteredReviews.map((review) => (
              <div key={review.id} className="bg-muted rounded-md transition-colors">
                <div className="flex w-full items-start justify-between p-4 hover:bg-muted/80 transition-colors rounded-md text-left">
                  <div className="flex-1 min-w-0">
                    <button
                      type="button"
                      className="block max-w-full font-semibold text-sm truncate cursor-pointer hover:text-primary hover:underline"
                      onClick={() => setSelectedPaperTitle(review.paper_title)}
                    >
                      {review.paper_title}
                    </button>
                    <p className="text-xs text-muted-foreground mb-2">
                      {review.pdf_filename} • {review.reviewer_model} • {formatDate(review.created_at)}
                    </p>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-semibold text-primary">
                        {review.score}/{maxScore}
                      </span>
                      <RecommendationBadge recommendation={review.recommendation} />
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">{review.review_summary}</p>
                  </div>
                  <div className="flex items-center gap-1 ml-4">
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => downloadPDF(review.id, review.pdf_filename)}
                        disabled={downloading === review.id || !review.pdf_path}
                        title={review.pdf_path ? "Download PDF" : "PDF not available"}
                        aria-label={`Download ${review.pdf_filename}`}
                      >
                        {downloading === review.id ? <Spinner label="Downloading" /> : <Download className="h-4 w-4" />}
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => deleteReview(review.id)}
                        disabled={deleting === review.id}
                        aria-label={`Delete review for ${review.paper_title}`}
                      >
                        {deleting === review.id ? <Spinner label="Deleting" /> : <Trash2 className="h-4 w-4" />}
                      </Button>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => toggleExpand(review.id)}
                      aria-label={`${expandedReview === review.id ? "Collapse" : "Expand"} review for ${review.paper_title}`}
                    >
                      {expandedReview === review.id ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                    </Button>
                  </div>
                </div>
                {expandedReview === review.id && (
                  <div className="px-4 pb-4 space-y-3 border-t border-border pt-4">
                    {loadingFull === review.id ? (
                      <LoadingBlock className="py-4" />
                    ) : fullReviewData[review.id] ? (
                      <ReviewDetails review={fullReviewData[review.id]} maxScore={maxScore} />
                    ) : null}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </CardContent>

      <Dialog open={selectedPaperTitle !== null} onOpenChange={(open) => !open && setSelectedPaperTitle(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reviews for Paper</DialogTitle>
            <DialogDescription>{selectedPaperTitle}</DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] space-y-3 overflow-y-auto">
            {reviews
              .filter((r) => r.paper_title === selectedPaperTitle)
              .map((r) => (
                <div key={r.id} className="space-y-2 rounded-md bg-muted p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-medium">🤖 {r.reviewer_model}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-primary">
                        {r.score}/{maxScore}
                      </span>
                      <RecommendationBadge recommendation={r.recommendation} />
                    </div>
                  </div>
                  <p className="break-all font-mono text-xs text-muted-foreground">ID: {r.id}</p>
                </div>
              ))}
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
