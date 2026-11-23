import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ResultsPanel from "@/features/review/ResultsPanel";
import ReviewForm from "@/features/review/ReviewForm";
import { ReviewProvider } from "@/features/review/review-context";
import { reviewFormProblem } from "@/lib/review-forms";
import { mockApi } from "../../helpers/fetch";
import { renderWithQuery } from "../../helpers/render";
import { FakeWebSocket, installFakeWebSocket } from "../../helpers/websocket";

const toast = vi.hoisted(() => vi.fn(() => ({ id: "t", dismiss: vi.fn(), update: vi.fn() })));
vi.mock("@/hooks/use-toast", () => ({ toast, useToast: () => ({ toast, toasts: [], dismiss: vi.fn() }) }));

const criteria = { score: 8, recommendation: "Accept", novelty: "Very novel", review_form_response: null };
const relatedPaper = {
  ref: "R1",
  title: "Prior Work",
  authors: ["A. Author", "B. Author"],
  year: 2024,
  url: "https://arxiv.org/abs/2401.00001",
  abstract: "",
  relation: "Same task, different method.",
};
const config = {
  engine: "ollama",
  model: "llama3:8b",
  detail: "detailed",
  mode: "sections",
  temperature: 0.7,
  context_length: 32768,
  paper_truncated: false,
  generation_calls: 9,
  form: "default",
  conference: null,
  review_form_name: null,
  vlm_model: null,
  figures_described: 0,
  related_work: true,
  gpu: 1,
  duration_seconds: 125.4,
};
const completed = {
  status: "completed",
  progress: 100,
  message: "Review complete!",
  review_id: "r1",
  results: {
    paper_title: "My Paper",
    reviews: [
      {
        paper_title: "My Paper",
        reviewer_model: "llama3:8b",
        criteria,
        raw_response: "{}",
        related_work: [relatedPaper],
        config,
      },
    ],
  },
};

function routes() {
  return {
    "GET /api/config": { max_score: 10, review_detail: "standard", review_mode: "single" },
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
    "GET /api/review-forms": { forms: [], count: 0 },
    "POST /api/upload": { session_id: "s1", filename: "paper.pdf", message: "ok" },
  };
}

function renderReviewPage() {
  const view = renderWithQuery(
    <ReviewProvider>
      <ReviewForm />
      <ResultsPanel />
    </ReviewProvider>,
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
    expect(url.searchParams.get("related")).toBe("true");
    expect(url.searchParams.get("detail")).toBe("standard"); // server defaults until the user picks
    expect(url.searchParams.get("mode")).toBe("single");
    expect(api.calls("POST /api/upload")).toBe(1);
    expect(screen.getByRole("button", { name: /Reviewing/ })).toBeDisabled();

    act(() => FakeWebSocket.last().receive({ status: "progress", progress: 50, message: "Reviewing" }));
    act(() => FakeWebSocket.last().receive(completed));

    expect(await screen.findByText("Very novel")).toBeInTheDocument();
    expect(screen.getByText("8/10")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Prior Work" })).toHaveAttribute(
      "href",
      "https://arxiv.org/abs/2401.00001",
    );
    expect(screen.getByText("Same task, different method.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Start Review/ })).toBeEnabled();
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ title: "✅ Review Complete" }));

    const settings = within(screen.getByLabelText("Review settings"));
    expect(settings.getByText("Section by section (9 calls)")).toBeInTheDocument();
    expect(settings.getByText("Detailed")).toBeInTheDocument();
    expect(settings.getByText("GPU 1")).toBeInTheDocument();
    expect(settings.getByText("2 min 5 s")).toBeInTheDocument();
  });

  it("sends the chosen review length and generation mode", async () => {
    mockApi(routes());
    const { pdfInput } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");
    await userEvent.selectOptions(screen.getByLabelText("Review Length"), "Detailed");
    await userEvent.selectOptions(screen.getByLabelText("Generation"), "Section by section");
    await userEvent.upload(pdfInput, pdf());
    await userEvent.click(screen.getByRole("button", { name: /Start Review/ }));

    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    const params = new URL(FakeWebSocket.last().url).searchParams;
    expect(params.get("detail")).toBe("detailed");
    expect(params.get("mode")).toBe("sections");
  });

  it("starts from the server's default length and mode", async () => {
    mockApi({ ...routes(), "GET /api/config": { max_score: 10, review_detail: "concise", review_mode: "sections" } });
    renderReviewPage();
    await waitFor(() => expect(screen.getByLabelText("Review Length")).toHaveValue("concise"));
    expect(screen.getByLabelText("Generation")).toHaveValue("sections");
  });

  it("can skip the related-work search", async () => {
    mockApi(routes());
    const { pdfInput } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");
    await userEvent.click(screen.getByLabelText("Search arXiv for related work"));
    await userEvent.upload(pdfInput, pdf());
    await userEvent.click(screen.getByRole("button", { name: /Start Review/ }));

    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    expect(new URL(FakeWebSocket.last().url).searchParams.get("related")).toBe("false");
  });

  it("shows each conference's page limit", async () => {
    const dac = {
      id: "dac",
      name: "DAC",
      full_name: "Design Automation Conference",
      area: "Design Automation",
      edition: "2026",
      verified: false,
      source_urls: [],
      question_count: 8,
      page_limit: { pages: 6, excludes: "references", note: "", edition: "2026", source_url: "https://dac.com/cfp" },
    };
    const noLimit = { ...dac, id: "other", name: "Other", page_limit: null };
    mockApi({
      ...routes(),
      "GET /api/conferences": { conferences: [dac, noLimit], count: 2 },
      "GET /api/conferences/dac": { ...dac, questions: [], form_markdown: "# DAC" },
    });
    renderReviewPage();

    const select = await screen.findByLabelText("Review Form");
    expect(await screen.findByRole("option", { name: "DAC 2026 · 6 pages" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Other 2026" })).toBeInTheDocument();

    await userEvent.selectOptions(select, "conference:dac");
    expect(screen.getByText(/6 pages, excluding references/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "DAC 2026 call for papers" })).toHaveAttribute(
      "href",
      "https://dac.com/cfp",
    );
    // Selecting a form no longer opens a preview; it is one link away in the Review Forms tab.
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View form" })).toHaveAttribute("href", "/forms?form=conference%3Adac");
  });

  it("asks for a name when a form is uploaded, saves it and reviews with it", async () => {
    const saved = {
      id: "a".repeat(32),
      name: "Workshop 2026",
      filename: "workshop_2026.md",
      created_at: "2026-11-23T00:00:00Z",
      size: 4,
    };
    let forms: (typeof saved)[] = [];
    let savedName: string | undefined;
    let uploadedFormId: string | undefined;
    // jsdom's File cannot be parsed back out of a multipart body, so read the text fields from the raw body.
    const field = async (request: Request, name: string) =>
      (await request.text()).match(new RegExp(`name="${name}"\\r\\n\\r\\n([^\\r]*)`))?.[1];
    mockApi({
      ...routes(),
      "GET /api/review-forms": () => ({ forms, count: forms.length }),
      "POST /api/review-forms": async (request: Request) => {
        savedName = await field(request, "name");
        forms = [saved];
        return { ...saved, content: "# Q1" };
      },
      "POST /api/upload": async (request: Request) => {
        uploadedFormId = await field(request, "review_form_id");
        return { session_id: "s1", filename: "paper.pdf" };
      },
    });
    const { pdfInput } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");

    await userEvent.upload(
      screen.getByLabelText("Review form file"),
      new File(["# Q1"], "workshop_2026.md", { type: "text/markdown" }),
    );
    const name = await screen.findByLabelText("Name");
    expect(name).toHaveValue("workshop 2026");
    await userEvent.clear(name);
    await userEvent.type(name, "Workshop 2026");
    await userEvent.click(screen.getByRole("button", { name: "Save Form" }));

    await waitFor(() => expect(screen.getByLabelText("Review Form")).toHaveValue(`custom:${saved.id}`));
    expect(savedName).toBe("Workshop 2026");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await userEvent.upload(pdfInput, pdf());
    await userEvent.click(screen.getByRole("button", { name: /Start Review/ }));
    await waitFor(() => expect(uploadedFormId).toBe(saved.id));
  });

  it("reports a failed review and lets the user retry", async () => {
    mockApi(routes());
    const { pdfInput } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");
    await userEvent.upload(pdfInput, pdf());
    await userEvent.click(screen.getByRole("button", { name: /Start Review/ }));
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));

    act(() => FakeWebSocket.last().receive({ status: "error", message: "Model crashed" }));

    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Review Failed", description: "Model crashed" }),
    );
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

    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Review Failed", description: "The review connection closed unexpectedly." }),
    );
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
