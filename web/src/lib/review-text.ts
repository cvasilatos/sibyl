import { saveText } from "@/lib/download";
import { reviewConfigRows } from "@/lib/review-config";
import type { RelatedPaper, Review, ReviewConfig } from "@/lib/types";

type ReviewLike = Pick<Review, "paper_title" | "reviewer_model" | "criteria"> &
  Partial<Pick<Review, "related_work" | "config">>;

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

function relatedWorkText(papers: RelatedPaper[]): string {
  const lines = papers.map((paper) => {
    const year = paper.year ? ` (${paper.year})` : "";
    const relation = paper.relation ? `\n     ${paper.relation}` : "";
    return `[${paper.ref}] ${paper.title}${year}. ${paper.url}${relation}`;
  });
  return `Related Work (arXiv)\n--------------------\n${lines.join("\n")}`;
}

function configText(config: ReviewConfig): string {
  const rows = reviewConfigRows(config).map(([label, value]) => `${label}: ${value}`);
  return `Settings Used\n-------------\n${rows.join("\n")}`;
}

/** Plain-text version of a review: the completed form when one was used, otherwise Sibyl's default sections. */
export function reviewToText(review: ReviewLike, maxScore?: number): string {
  const { criteria } = review;
  const score = maxScore ? `${criteria.score}/${maxScore}` : String(criteria.score);
  const header = [
    `Paper: ${review.paper_title}`,
    `Reviewer model: ${review.reviewer_model}`,
    `Overall score: ${score}`,
    `Recommendation: ${criteria.recommendation}`,
  ];
  const body = criteria.review_form_response
    ? [criteria.review_form_response]
    : DEFAULT_SECTIONS.map(({ title, field }) => `${title}\n${"-".repeat(title.length)}\n${criteria[field]}`);
  const related = review.related_work?.length ? [relatedWorkText(review.related_work)] : [];
  const settings = review.config ? [configText(review.config)] : [];
  return `${[header.join("\n"), ...body, ...related, ...settings].join("\n\n")}\n`;
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
