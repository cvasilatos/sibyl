import { FileText } from "lucide-react";
import RelatedWorkList from "@/components/RelatedWorkList";
import ReviewConfigPanel from "@/components/ReviewConfigPanel";
import ReviewSection from "@/components/ReviewSection";
import { Button } from "@/components/ui/button";
import { DEFAULT_SECTIONS, downloadReviewText } from "@/lib/review-text";
import type { Review } from "@/lib/types";

const SECTION_ICONS: Record<string, string> = {
  novelty: "💡",
  methodology: "🔬",
  results: "📈",
  clarity: "✍️",
  impact: "🎯",
  strengths: "💪",
  limitations: "⚠️",
  detailed_feedback: "📝",
};

export default function ReviewDetails({
  review,
  maxScore,
}: {
  review: Pick<Review, "paper_title" | "reviewer_model" | "criteria" | "related_work"> &
    Partial<Pick<Review, "config">>;
  maxScore?: number;
}) {
  const { criteria } = review;
  return (
    <>
      <div className="flex justify-end">
        <Button
          size="sm"
          variant="outline"
          onClick={() => downloadReviewText(review, maxScore)}
          aria-label={`Download review of ${review.paper_title} as text`}
        >
          <FileText className="h-4 w-4 mr-1" /> Download .txt
        </Button>
      </div>
      {criteria.review_form_response ? (
        <ReviewSection
          title={criteria.conference ? "📋 Conference Reviewer Form" : "📋 Completed Review Form"}
          content={criteria.review_form_response}
        />
      ) : (
        DEFAULT_SECTIONS.map(({ title, field }) => (
          <ReviewSection key={field} title={`${SECTION_ICONS[field]} ${title}`} content={String(criteria[field])} />
        ))
      )}
      {review.related_work.length > 0 && <RelatedWorkList papers={review.related_work} />}
      {review.config && <ReviewConfigPanel config={review.config} />}
    </>
  );
}
