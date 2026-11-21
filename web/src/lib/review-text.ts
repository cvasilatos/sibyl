import { saveText } from "@/lib/download";
import type { Review } from "@/lib/types";

type ReviewLike = Pick<Review, "paper_title" | "reviewer_model" | "criteria">;

export const DEFAULT_SECTIONS = [
  { title: "Novelty", field: "novelty" },
  { title: "Methodology", field: "methodology" },
  { title: "Results", field: "results" },
  { title: "Clarity", field: "clarity" },
  { title: "Impact", field: "impact" },
  { title: "Strengths", field: "strengths" },
  { title: "Limitations", field: "limitations" },
  { title: "Detailed Feedback", field: "detailed_feedback" },
] as const;

/** Plain-text version of a review: the completed form when one was used, otherwise Sibyl's default sections. */
export function reviewToText(review: ReviewLike, maxScore?: number): string {
  const { criteria } = review;
  const score = maxScore ? `${criteria.score}/${maxScore}` : String(criteria.score);
  const header = [`Paper: ${review.paper_title}`, `Reviewer model: ${review.reviewer_model}`, `Overall score: ${score}`, `Recommendation: ${criteria.recommendation}`];
  const body = criteria.review_form_response
    ? [criteria.review_form_response]
    : DEFAULT_SECTIONS.map(({ title, field }) => `${title}\n${"-".repeat(title.length)}\n${criteria[field]}`);
  return `${[header.join("\n"), ...body].join("\n\n")}\n`;
}

export function reviewFileName(review: ReviewLike): string {
  const slug = (text: string) =>
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60);
  const kind = review.criteria.conference ? `-${slug(review.criteria.conference)}` : "";
  return `review-${slug(review.paper_title) || "paper"}${kind}-${slug(review.reviewer_model) || "model"}.txt`;
}

export function downloadReviewText(review: ReviewLike, maxScore?: number): void {
  saveText(reviewToText(review, maxScore), reviewFileName(review));
}
