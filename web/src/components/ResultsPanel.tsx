import ReviewSection from "@/components/ReviewSection";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

type ReviewCriteria = {
  novelty: string;
  methodology: string;
  results: string;
  clarity: string;
  impact: string;
  limitations: string;
  strengths: string;
  score: number;
  recommendation: string;
  detailed_feedback: string;
};

type Review = {
  paper_title: string;
  reviewer_model: string;
  criteria: ReviewCriteria;
  raw_response: string;
};

type ReviewResults = {
  paper_title: string;
  reviews: Review[];
};

export default function ResultsPanel({ results, getRecommendationColor, maxScore }: { results: ReviewResults; getRecommendationColor: (rec: string) => string; maxScore: number }) {
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
                <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getRecommendationColor(review.criteria.recommendation)}`}>{review.criteria.recommendation}</span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <ReviewSection title="💡 Novelty" content={review.criteria.novelty} />
            <ReviewSection title="🔬 Methodology" content={review.criteria.methodology} />
            <ReviewSection title="📈 Results" content={review.criteria.results} />
            <ReviewSection title="✍️ Clarity" content={review.criteria.clarity} />
            <ReviewSection title="🎯 Impact" content={review.criteria.impact} />
            <ReviewSection title="💪 Strengths" content={review.criteria.strengths} />
            <ReviewSection title="⚠️ Limitations" content={review.criteria.limitations} />
            <ReviewSection title="📝 Detailed Feedback" content={review.criteria.detailed_feedback} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
