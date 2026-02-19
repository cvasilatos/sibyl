import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import ReviewSection from "@/components/ReviewSection"

type ComparisonStats = {
  mean: number
  std: number
  min: number
  max: number
}

type ReviewCriteria = {
  novelty: string
  methodology: string
  results: string
  clarity: string
  impact: string
  limitations: string
  strengths: string
  overall_score: number
  recommendation: string
  detailed_feedback: string
}

type Review = {
  paper_title: string
  reviewer_model: string
  criteria: ReviewCriteria
}

type ReviewResults = {
  paper_title: string
  reviews: Review[]
  comparison: {
    score_statistics: ComparisonStats
    consensus: string
    total_reviews: number
    reviewers: string[]
  }
}

export default function ResultsPanel({
  results,
  getRecommendationColor,
}: {
  results: ReviewResults
  getRecommendationColor: (rec: string) => string
}) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>📊 Overall Statistics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex justify-between">
            <span className="font-medium">Mean Score:</span>
            <span className="text-primary font-semibold">{results.comparison.score_statistics.mean.toFixed(2)}/10</span>
          </div>
          <div className="flex justify-between">
            <span className="font-medium">Standard Deviation:</span>
            <span>{results.comparison.score_statistics.std.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="font-medium">Score Range:</span>
            <span>
              {results.comparison.score_statistics.min} - {results.comparison.score_statistics.max}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="font-medium">Consensus:</span>
            <span className="font-semibold">{results.comparison.consensus}</span>
          </div>
        </CardContent>
      </Card>

      {results.reviews.map((review, index) => (
        <Card key={index}>
          <CardHeader>
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-2 font-semibold">
                🤖 {review.reviewer_model}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-3xl font-bold text-primary">{review.criteria.overall_score}/10</span>
                <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getRecommendationColor(review.criteria.recommendation)}`}>
                  {review.criteria.recommendation}
                </span>
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
  )
}
