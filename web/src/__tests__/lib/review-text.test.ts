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
    expect(text).toContain(
      "Paper: Attention Is All You Need!\nReviewer model: qwen3:8b\nOverall score: 7/10\nRecommendation: Accept",
    );
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

describe("reviewToText related work", () => {
  it("lists the related papers the review cites", () => {
    const related_work = [
      {
        ref: "R1",
        title: "Prior Work",
        authors: [],
        year: 2024,
        url: "https://arxiv.org/abs/1",
        abstract: "",
        relation: "Same task.",
      },
    ];
    const text = reviewToText({ ...review, related_work });
    expect(text).toContain(
      "Related Work\n------------\n[R1] Prior Work (2024). https://arxiv.org/abs/1\n     Same task.\n",
    );
  });
});

describe("reviewFileName", () => {
  it("slugs the title and model, and adds the conference", () => {
    expect(reviewFileName(review)).toBe("review-attention-is-all-you-need-qwen3-8b.txt");
    expect(reviewFileName({ ...review, criteria: { ...criteria, conference: "NeurIPS 2025" } })).toBe(
      "review-attention-is-all-you-need-neurips-2025-qwen3-8b.txt",
    );
  });

  it("falls back when the title has no usable characters", () => {
    expect(reviewFileName({ ...review, paper_title: "???" })).toBe("review-paper-qwen3-8b.txt");
  });
});

describe("reviewToText settings", () => {
  it("ends with the settings that produced the review", () => {
    const config = {
      engine: "vllm",
      model: "qwen3:8b",
      detail: "concise",
      mode: "single",
      temperature: 0.2,
      context_length: 16384,
      paper_truncated: true,
      generation_calls: 1,
      form: "conference",
      conference: "NeurIPS 2025",
      review_form_name: null,
      vlm_model: "qwen2.5vl:7b",
      figures_described: 3,
      related_work: false,
      gpu: null,
      duration_seconds: 42,
    } as const;
    const text = reviewToText({ ...review, config });
    expect(text).toContain(
      "Settings Used\n-------------\nModel: qwen3:8b\nEngine: vllm\nReview length: Concise\nGeneration: Whole review at once (1 call)",
    );
    expect(text).toContain("Review form: NeurIPS 2025 reviewer form");
    expect(text).toContain("Context window: 16,384 tokens (paper end trimmed)");
    expect(text).toContain("Figures: qwen2.5vl:7b (3 described)");
    expect(text).toContain("GPU: Auto");
    expect(text).toContain("Time taken: 42 s");
  });

  it("leaves the settings out for reviews saved before they were recorded", () => {
    expect(reviewToText(review)).not.toContain("Settings Used");
  });
});
