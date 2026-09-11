import ReviewSection from "@/components/ReviewSection";
import type { ReviewCriteria } from "@/lib/types";

const REVIEW_SECTIONS: Array<{ title: string; field: keyof ReviewCriteria }> = [
  { title: "💡 Novelty", field: "novelty" },
  { title: "🔬 Methodology", field: "methodology" },
  { title: "📈 Results", field: "results" },
  { title: "✍️ Clarity", field: "clarity" },
  { title: "🎯 Impact", field: "impact" },
  { title: "💪 Strengths", field: "strengths" },
  { title: "⚠️ Limitations", field: "limitations" },
  { title: "📝 Detailed Feedback", field: "detailed_feedback" },
];

export default function ReviewDetails({ criteria }: { criteria: ReviewCriteria }) {
  return REVIEW_SECTIONS.map(({ title, field }) => <ReviewSection key={field} title={title} content={String(criteria[field])} />);
}
