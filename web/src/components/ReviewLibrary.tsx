"use client";

import { ChevronDown, ChevronUp, Download, Loader2, RefreshCw, Search, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReviewDetails from "@/components/ReviewDetails";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { fetchMaxScore } from "@/lib/config";
import { formatDate, recommendationClassName } from "@/lib/presentation";
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
    fetchMaxScore()
      .then(setMaxScore)
      .catch((err) => {
        console.error("Failed to load max score:", err);
        toast({ title: "Warning", description: "Could not load score scale from server, using default.", variant: "destructive" });
      });
  }, [loadReviews]);

  // Auto-fetch full review data when linked directly to an expanded review
  useEffect(() => {
    if (!initialExpandedReview) return;
    const controller = new AbortController();
    setLoadingFull(initialExpandedReview);
    api
      .getReview(initialExpandedReview, controller.signal)
      .then((data: FullReview) => {
        setFullReviewData((prev) => ({ ...prev, [initialExpandedReview]: data }));
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to load review details");
        setExpandedReview(null);
      })
      .finally(() => {
        setLoadingFull(null);
      });
    return () => controller.abort();
  }, [initialExpandedReview]);

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
      const blob = await api.downloadReviewPdf(reviewId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download PDF");
    } finally {
      setDownloading(null);
    }
  };

  const toggleExpand = async (reviewId: string) => {
    if (expandedReview === reviewId) {
      setExpandedReview(null);
      onReviewExpand?.(null);
      return;
    }

    setExpandedReview(reviewId);
    onReviewExpand?.(reviewId);

    if (!fullReviewData[reviewId]) {
      setLoadingFull(reviewId);
      try {
        const data = await api.getReview(reviewId);
        setFullReviewData((prev) => ({ ...prev, [reviewId]: data }));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load review details");
        setExpandedReview(null);
      } finally {
        setLoadingFull(null);
      }
    }
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
              {deletingAll ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
              Delete All
            </Button>
            <Button onClick={loadReviews} disabled={loading} size="sm" variant="outline">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="p-3 bg-destructive/10 border border-destructive rounded-md">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

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
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            placeholder="Search reviews by title, model, recommendation…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-md border border-input bg-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        {/* Reviews list */}
        <div className="space-y-2">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
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
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${recommendationClassName(review.recommendation)}`}>{review.recommendation}</span>
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
                        {downloading === review.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => deleteReview(review.id)}
                        disabled={deleting === review.id}
                        aria-label={`Delete review for ${review.paper_title}`}
                      >
                        {deleting === review.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
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
                      <div className="flex items-center justify-center py-4">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                      </div>
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

      {/* Paper reviews panel */}
      {selectedPaperTitle && (
        <div className="fixed inset-0 z-50 flex w-full items-center justify-center">
          <button type="button" className="absolute inset-0 bg-black/50" aria-label="Close paper reviews dialog" onClick={() => setSelectedPaperTitle(null)} />
          <div role="dialog" aria-modal="true" className="relative z-10 bg-background rounded-lg shadow-xl max-w-lg w-full mx-4 p-6">
            <div className="flex items-start justify-between mb-4 gap-4">
              <div>
                <h2 className="font-semibold text-lg">Reviews for Paper</h2>
                <p className="text-sm text-muted-foreground mt-1">{selectedPaperTitle}</p>
              </div>
              <Button size="sm" variant="outline" onClick={() => setSelectedPaperTitle(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="space-y-3 max-h-[60vh] overflow-y-auto">
              {reviews
                .filter((r) => r.paper_title === selectedPaperTitle)
                .map((r) => (
                  <div key={r.id} className="p-3 bg-muted rounded-md space-y-2">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <span className="text-sm font-medium">🤖 {r.reviewer_model}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-primary">
                          {r.score}/{maxScore}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${recommendationClassName(r.recommendation)}`}>{r.recommendation}</span>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground font-mono break-all">ID: {r.id}</p>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
