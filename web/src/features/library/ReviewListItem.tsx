"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, Download, Trash2 } from "lucide-react";
import RecommendationBadge from "@/components/RecommendationBadge";
import ReviewDetails from "@/components/ReviewDetails";
import { ErrorAlert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { LoadingBlock, Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import { queries } from "@/lib/api/queries";
import { saveBlob } from "@/lib/download";
import { formatDate } from "@/lib/format";
import type { StoredReview } from "@/lib/types";

type Props = {
  review: StoredReview;
  maxScore: number;
  expanded: boolean;
  onToggle: () => void;
  onShowPaper: () => void;
  /** Deletes the review; omitted when the user may not (only its owner and admins may). */
  onDelete?: () => void;
  deleting: boolean;
  onError: (message: string) => void;
};

/** One stored review: summary row with actions, and the full review when expanded. */
export default function ReviewListItem({
  review,
  maxScore,
  expanded,
  onToggle,
  onShowPaper,
  onDelete,
  deleting,
  onError,
}: Props) {
  const details = useQuery({ ...queries.review(review.id), enabled: expanded });
  const downloadPdf = useMutation({
    mutationFn: () => api.downloadReviewPdf(review.id),
    onSuccess: (blob) => saveBlob(blob, review.pdf_filename),
    onError: (err) => onError(err.message || "Failed to download PDF"),
  });

  return (
    <div className="rounded-md bg-muted transition-colors">
      <div className="flex w-full items-start justify-between rounded-md p-4 text-left transition-colors hover:bg-muted/80">
        <div className="min-w-0 flex-1">
          <button
            type="button"
            className="block max-w-full cursor-pointer truncate text-sm font-semibold hover:text-primary hover:underline"
            onClick={onShowPaper}
          >
            {review.paper_title}
          </button>
          <p className="mb-2 text-xs text-muted-foreground">
            {review.pdf_filename} • {review.reviewer_model} • {formatDate(review.created_at)}
            {review.owner ? ` • by ${review.owner}` : ""}
          </p>
          <div className="mb-2 flex items-center gap-2">
            <span className="text-sm font-semibold text-primary">
              {review.score}/{maxScore}
            </span>
            <RecommendationBadge recommendation={review.recommendation} />
          </div>
          <p className="line-clamp-2 text-xs text-muted-foreground">{review.review_summary}</p>
        </div>
        <div className="ml-4 flex items-center gap-1">
          <Button
            size="sm"
            variant="outline"
            onClick={() => downloadPdf.mutate()}
            disabled={downloadPdf.isPending || !review.pdf_path}
            title={review.pdf_path ? "Download PDF" : "PDF not available"}
            aria-label={`Download ${review.pdf_filename}`}
          >
            {downloadPdf.isPending ? <Spinner label="Downloading" /> : <Download className="h-4 w-4" />}
          </Button>
          {onDelete && (
            <Button
              size="sm"
              variant="destructive"
              onClick={onDelete}
              disabled={deleting}
              aria-label={`Delete review for ${review.paper_title}`}
            >
              {deleting ? <Spinner label="Deleting" /> : <Trash2 className="h-4 w-4" />}
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={onToggle}
            aria-expanded={expanded}
            aria-label={`${expanded ? "Collapse" : "Expand"} review for ${review.paper_title}`}
          >
            {expanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </Button>
        </div>
      </div>
      {expanded && (
        <div className="space-y-3 border-t border-border px-4 pb-4 pt-4">
          {details.isPending ? (
            <LoadingBlock className="py-4" />
          ) : details.isError ? (
            <ErrorAlert>{details.error.message || "Failed to load review details"}</ErrorAlert>
          ) : (
            <ReviewDetails review={details.data} maxScore={maxScore} />
          )}
        </div>
      )}
    </div>
  );
}
