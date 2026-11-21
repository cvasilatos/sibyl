import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ResultsPanel from "@/features/review/ResultsPanel";
import ReviewForm from "@/features/review/ReviewForm";
import { ReviewProvider, reviewFormProblem } from "@/features/review/review-context";
import { mockApi } from "../../helpers/fetch";
import { renderWithQuery } from "../../helpers/render";
import { FakeWebSocket, installFakeWebSocket } from "../../helpers/websocket";

const toast = vi.hoisted(() => vi.fn(() => ({ id: "t", dismiss: vi.fn(), update: vi.fn() })));
vi.mock("@/hooks/use-toast", () => ({ toast, useToast: () => ({ toast, toasts: [], dismiss: vi.fn() }) }));

const criteria = { score: 8, recommendation: "Accept", novelty: "Very novel", review_form_response: null };
const completed = {
  status: "completed",
  progress: 100,
  message: "Review complete!",
  review_id: "r1",
  results: { paper_title: "My Paper", reviews: [{ paper_title: "My Paper", reviewer_model: "llama3:8b", criteria, raw_response: "{}" }] },
};

function routes() {
  return {
    "GET /api/config": { max_score: 10 },
    "GET /api/models": {
      models: [
        { model: "qwen3:8b", size: 1, digest: "a", modified_at: "2026-01-01" },
        { model: "llama3:8b", size: 1, digest: "b", modified_at: "2026-01-01" },
      ],
    },
    "GET /api/gpu": {
      available: true,
      count: 2,
      gpus: [
        { index: 0, name: "GPU A" },
        { index: 1, name: "GPU B" },
      ],
    },
    "GET /api/conferences": { conferences: [], count: 0 },
    "POST /api/upload": { session_id: "s1", filename: "paper.pdf", message: "ok" },
  };
}

function renderReviewPage() {
  const view = renderWithQuery(
    <ReviewProvider>
      <ReviewForm />
      <ResultsPanel />
    </ReviewProvider>
  );
  const pdfInput = view.container.querySelector<HTMLInputElement>('input[accept=".pdf"]');
  if (!pdfInput) throw new Error("PDF input not found");
  return { ...view, pdfInput };
}

const pdf = () => new File(["%PDF"], "paper.pdf", { type: "application/pdf" });

describe("review flow", () => {
  beforeEach(() => {
    installFakeWebSocket();
    toast.mockClear();
  });

  it("uploads the paper, follows the session and shows the results", async () => {
    const api = mockApi(routes());
    const { pdfInput } = renderReviewPage();
    await userEvent.selectOptions(await screen.findByLabelText("Select Model for Review"), "llama3:8b");
    await userEvent.selectOptions(await screen.findByLabelText("Select GPU"), "1");
    await userEvent.selectOptions(await screen.findByLabelText("Vision Model for Figures"), "None (captions only)");
    await userEvent.upload(pdfInput, pdf());
    await userEvent.click(screen.getByRole("button", { name: /Start Review/ }));

    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    const url = new URL(FakeWebSocket.last().url);
    expect(url.pathname).toBe("/ws/session/s1");
    expect(url.searchParams.get("model")).toBe("llama3:8b");
    expect(url.searchParams.get("host")).toBe("2"); // GPU 1 is host 2; 0 means any
    expect(url.searchParams.get("vlm")).toBe("none");
    expect(api.calls("POST /api/upload")).toBe(1);
    expect(screen.getByRole("button", { name: /Reviewing/ })).toBeDisabled();

    act(() => FakeWebSocket.last().receive({ status: "progress", progress: 50, message: "Reviewing" }));
    act(() => FakeWebSocket.last().receive(completed));

    expect(await screen.findByText("Very novel")).toBeInTheDocument();
    expect(screen.getByText("8/10")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Start Review/ })).toBeEnabled();
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ title: "✅ Review Complete" }));
  });

  it("reports a failed review and lets the user retry", async () => {
    mockApi(routes());
    const { pdfInput } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");
    await userEvent.upload(pdfInput, pdf());
    await userEvent.click(screen.getByRole("button", { name: /Start Review/ }));
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));

    act(() => FakeWebSocket.last().receive({ status: "error", message: "Model crashed" }));

    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ title: "Review Failed", description: "Model crashed" }));
    expect(screen.getByRole("button", { name: /Start Review/ })).toBeEnabled();
  });

  it("treats a connection that closes early as a failure", async () => {
    mockApi(routes());
    const { pdfInput } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");
    await userEvent.upload(pdfInput, pdf());
    await userEvent.click(screen.getByRole("button", { name: /Start Review/ }));
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));

    act(() => FakeWebSocket.last().serverClose());

    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ title: "Review Failed", description: "The review connection closed unexpectedly." }));
  });

  it("rejects a file that is not a PDF", async () => {
    mockApi(routes());
    const { pdfInput } = renderReviewPage();
    await userEvent.upload(pdfInput, new File(["x"], "notes.txt", { type: "text/plain" }), { applyAccept: false });
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ title: "Invalid File" }));
    expect(screen.getByRole("button", { name: /Start Review/ })).toBeDisabled();
  });
});

describe("reviewFormProblem", () => {
  it("accepts small text and Markdown files", () => {
    expect(reviewFormProblem(new File(["# Q1"], "form.MD"))).toBeNull();
  });

  it("rejects other extensions and files over 64 KiB", () => {
    expect(reviewFormProblem(new File(["x"], "form.pdf"))).toMatch(/\.txt/);
    expect(reviewFormProblem(new File(["x".repeat(64 * 1024 + 1)], "form.txt"))).toMatch(/64 KiB/);
  });
});
