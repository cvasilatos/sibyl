"use client";

import RecommendationBadge from "@/components/RecommendationBadge";
import ReviewDetails from "@/components/ReviewDetails";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useReview } from "./review-context";

/** The reviews of the last completed run, one card per reviewer model. */
export default function ResultsPanel() {
  const { results, maxScore } = useReview();
  if (!results) return null;
  return (
    <div className="space-y-6">
      {results.reviews.map((review) => (
        <Card key={review.reviewer_model}>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2 font-semibold">🤖 {review.reviewer_model}</div>
              <div className="flex items-center gap-2">
                <span className="text-3xl font-bold text-primary">
                  {review.criteria.score}/{maxScore}
                </span>
                <RecommendationBadge recommendation={review.criteria.recommendation} size="md" />
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
