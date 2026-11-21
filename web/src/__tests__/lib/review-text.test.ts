import { describe, expect, it } from "vitest";
import { reviewFileName, reviewToText } from "@/lib/review-text";
import type { ReviewCriteria } from "@/lib/types";

const criteria: ReviewCriteria = {
  novelty: "Novel",
  methodology: "Sound",
  results: "Strong",
  clarity: "Clear",
  impact: "High",
  limitations: "Few",
  strengths: "Many",
  score: 7,
  recommendation: "Accept",
  detailed_feedback: "Good work",
  review_form_response: null,
  conference: null,
  review_form_answers: null,
};
const review = { paper_title: "Attention Is All You Need!", reviewer_model: "qwen3:8b", criteria };

describe("reviewToText", () => {
  it("writes the header and Sibyl's default sections", () => {
    const text = reviewToText(review, 10);
    expect(text).toContain("Paper: Attention Is All You Need!\nReviewer model: qwen3:8b\nOverall score: 7/10\nRecommendation: Accept");
    expect(text).toContain("Novelty\n-------\nNovel");
    expect(text).toContain("Detailed Feedback\n-----------------\nGood work");
  });

  it("uses the completed form instead of the default sections when there is one", () => {
    const text = reviewToText({ ...review, criteria: { ...criteria, review_form_response: "Q1: yes" } });
    expect(text).toContain("Overall score: 7\n");
    expect(text).toContain("Q1: yes");
    expect(text).not.toContain("Novelty");
  });
});

describe("reviewFileName", () => {
  it("slugs the title and model, and adds the conference", () => {
    expect(reviewFileName(review)).toBe("review-attention-is-all-you-need-qwen3-8b.txt");
    expect(reviewFileName({ ...review, criteria: { ...criteria, conference: "NeurIPS 2025" } })).toBe("review-attention-is-all-you-need-neurips-2025-qwen3-8b.txt");
  });

  it("falls back when the title has no usable characters", () => {
    expect(reviewFileName({ ...review, paper_title: "???" })).toBe("review-paper-qwen3-8b.txt");
  });
});
