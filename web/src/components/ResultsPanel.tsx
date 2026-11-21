import ReviewDetails from "@/components/ReviewDetails";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { recommendationClassName } from "@/lib/presentation";
import type { ReviewResults } from "@/lib/types";

export default function ResultsPanel({ results, maxScore }: { results: ReviewResults; maxScore: number }) {
  return (
    <div className="space-y-6">
      {results.reviews.map((review) => (
        <Card key={review.reviewer_model}>
          <CardHeader>
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-2 font-semibold">🤖 {review.reviewer_model}</div>
              <div className="flex items-center gap-2">
                <span className="text-3xl font-bold text-primary">
                  {review.criteria.score}/{maxScore}
                </span>
                <span className={`px-3 py-1 rounded-full text-sm font-semibold ${recommendationClassName(review.criteria.recommendation)}`}>{review.criteria.recommendation}</span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <ReviewDetails review={review} maxScore={maxScore} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
