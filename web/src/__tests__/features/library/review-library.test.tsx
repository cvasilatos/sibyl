import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import ReviewLibrary from "@/features/library/ReviewLibrary";
import { mockApi } from "../../helpers/fetch";
import { renderWithQuery } from "../../helpers/render";

function stored(id: string, paper_title: string, reviewer_model: string, recommendation = "Accept") {
  return {
    id,
    paper_title,
    pdf_filename: `${id}.pdf`,
    pdf_path: `/pdfs/${id}.pdf`,
    reviewer_model,
    score: 7,
    recommendation,
    created_at: "2026-01-01T00:00:00",
    review_summary: `Summary of ${id}`,
  };
}

const reviews = [stored("r1", "Paper One", "qwen3:8b"), stored("r2", "Paper Two", "llama3:8b", "Reject")];
const full = (id: string) => ({
  ...stored(id, "Paper One", "qwen3:8b"),
  criteria: { score: 7, recommendation: "Accept", novelty: `Novelty of ${id}` },
  raw_response: "{}",
  related_work: [],
});

function routes(overrides: Record<string, unknown> = {}) {
  return {
    "GET /api/config": { max_score: 10 },
    "GET /api/reviews": { reviews, count: reviews.length },
    "GET /api/statistics": { total_reviews: 2, unique_papers: 2, unique_models: 2, recommendations: {} },
    "GET /api/reviews/r1": full("r1"),
    ...overrides,
  };
}

/** The library with its expanded review held in state, as the page holds it in the URL. */
function Library({ initial = null }: { initial?: string | null }) {
  const [expanded, setExpanded] = useState<string | null>(initial);
  return <ReviewLibrary expandedReviewId={expanded} onExpandedChange={setExpanded} />;
}

describe("ReviewLibrary", () => {
  it("lists reviews with statistics and filters them by search", async () => {
    mockApi(routes());
    renderWithQuery(<Library />);
    expect(await screen.findByText("Paper One")).toBeInTheDocument();
    expect(screen.getByText("Paper Two")).toBeInTheDocument();
    expect(screen.getByText("Unique Papers")).toBeInTheDocument();

    await userEvent.type(screen.getByRole("searchbox"), "reject");
    expect(screen.queryByText("Paper One")).not.toBeInTheDocument();
    expect(screen.getByText("Paper Two")).toBeInTheDocument();
  });

  it("loads a review's details once, however often it is expanded", async () => {
    const api = mockApi(routes());
    renderWithQuery(<Library />);
    const toggle = await screen.findByRole("button", { name: "Expand review for Paper One" });

    await userEvent.click(toggle);
    expect(await screen.findByText("Novelty of r1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Collapse review for Paper One" }));
    await userEvent.click(screen.getByRole("button", { name: "Expand review for Paper One" }));
    expect(await screen.findByText("Novelty of r1")).toBeInTheDocument();
    expect(api.calls("GET /api/reviews/r1")).toBe(1);
  });

  it("opens a review linked from the URL", async () => {
    mockApi(routes());
    renderWithQuery(<Library initial="r1" />);
    expect(await screen.findByText("Novelty of r1")).toBeInTheDocument();
  });

  it("deletes a review after confirmation and reloads the list", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    let current = reviews;
    const api = mockApi(
      routes({
        "GET /api/reviews": () => ({ reviews: current, count: current.length }),
        "DELETE /api/reviews/r2": () => {
          current = reviews.filter((r) => r.id !== "r2");
          return { message: "deleted" };
        },
      })
    );
    renderWithQuery(<Library />);
    await userEvent.click(await screen.findByRole("button", { name: "Delete review for Paper Two" }));

    await waitFor(() => expect(screen.queryByText("Paper Two")).not.toBeInTheDocument());
    expect(api.calls("DELETE /api/reviews/r2")).toBe(1);
    expect(api.calls("GET /api/reviews")).toBe(2);
  });

  it("shows the backend's message when a deletion fails", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockApi(routes({ "DELETE /api/reviews/r1": new Response(JSON.stringify({ detail: "Storage is read-only" }), { status: 500 }) }));
    renderWithQuery(<Library />);
    await userEvent.click(await screen.findByRole("button", { name: "Delete review for Paper One" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Storage is read-only");
  });
});
