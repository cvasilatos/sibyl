import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ResultsPanel from "@/features/review/ResultsPanel";
import ReviewForm from "@/features/review/ReviewForm";
import ReviewQueue from "@/features/review/ReviewQueue";
import { ReviewProvider } from "@/features/review/review-context";
import { reviewFormProblem } from "@/lib/review-forms";
import { mockApi } from "../../helpers/fetch";
import { renderWithQuery } from "../../helpers/render";

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
const results = {
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
};

type Job = Record<string, unknown> & { id: string; status: string };

function job(overrides: Partial<Job> = {}): Job {
  return {
    id: "j1",
    owner: "local",
    filename: "paper.pdf",
    model: "llama3:8b",
    form_name: null,
    status: "queued",
    position: 1,
    requested_gpu: null,
    gpu: null,
    steps: ["parse", "review", "save"],
    step: null,
    progress: 0,
    message: "Waiting for a free GPU",
    created_at: "2026-11-25T10:00:00Z",
    started_at: null,
    finished_at: null,
    review_id: null,
    results: null,
    ...overrides,
  };
}

/** The server's review queue, which tests change between reads. */
let queue: Job[] = [];

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
    "GET /api/review-jobs": () => ({ jobs: queue, slots: 2 }),
    "POST /api/review-jobs": () => {
      queue = [job()];
      return queue[0];
    },
    "DELETE /api/review-jobs/j1": () => {
      queue = [job({ status: "cancelled", message: "Cancelled by local", position: null })];
      return queue[0];
    },
  };
}

function renderReviewPage() {
  const view = renderWithQuery(
    <ReviewProvider>
      <ReviewForm />
      <ReviewQueue />
      <ResultsPanel />
    </ReviewProvider>,
  );
  const pdfInput = view.container.querySelector<HTMLInputElement>('input[accept=".pdf"]');
  if (!pdfInput) throw new Error("PDF input not found");
  /** Make the server's queue `jobs` and let the page read it (it polls; tests do not wait for that). */
  const serverHas = async (...jobs: Job[]) => {
    queue = jobs;
    await act(() => view.client.invalidateQueries({ queryKey: ["reviewJobs"] }));
    await waitFor(() => expect(view.client.getQueryData<{ jobs: Job[] }>(["reviewJobs"])?.jobs).toEqual(jobs));
  };
  return { ...view, pdfInput, serverHas };
}

const pdf = () => new File(["%PDF"], "paper.pdf", { type: "application/pdf" });

async function submitPaper(pdfInput: HTMLInputElement) {
  await userEvent.upload(pdfInput, pdf());
  await userEvent.click(screen.getByRole("button", { name: /Start Review/ }));
}

describe("review flow", () => {
  beforeEach(() => {
    queue = [];
    toast.mockClear();
  });

  it("queues the paper with the chosen settings, follows it and shows the results", async () => {
    const api = mockApi(routes());
    const { pdfInput, serverHas } = renderReviewPage();
    await userEvent.selectOptions(await screen.findByLabelText("Select Model for Review"), "llama3:8b");
    await userEvent.selectOptions(await screen.findByLabelText("Select GPU"), "1");
    await userEvent.selectOptions(await screen.findByLabelText("Vision Model for Figures"), "None (captions only)");
    await submitPaper(pdfInput);

    await waitFor(() => expect(api.calls("POST /api/review-jobs")).toBe(1));
    const [fields = {}] = await api.formFields("POST /api/review-jobs");
    expect(fields).toEqual({
      model: "llama3:8b",
      gpu: "1",
      vlm: "none",
      related: "true",
      sources: "arxiv,semantic_scholar",
      detail: "standard", // server defaults until the user picks
      mode: "single",
    });
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ title: "Review Queued" }));
    // Queued: the paper is cleared so the next one can be picked while this one waits.
    await waitFor(() => expect(screen.getByRole("button", { name: /Start Review/ })).toBeDisabled());
    expect(await screen.findByText("Queued: #1 in line")).toBeInTheDocument();

    await serverHas(
      job({ status: "running", position: null, gpu: 1, step: "review", progress: 50, message: "Reviewing" }),
    );
    expect(await screen.findByText("Reviewing…")).toBeInTheDocument();
    await serverHas(job({ status: "completed", position: null, gpu: 1, progress: 100, review_id: "r1", results }));

    expect(await screen.findByText("Very novel")).toBeInTheDocument();
    expect(screen.getByText("8/10")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Prior Work" })).toHaveAttribute(
      "href",
      "https://arxiv.org/abs/2401.00001",
    );
    expect(screen.getByText("Same task, different method.")).toBeInTheDocument();
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ title: "✅ Review Complete" }));

    const settings = within(screen.getByLabelText("Review settings"));
    expect(settings.getByText("Section by section (9 calls)")).toBeInTheDocument();
    expect(settings.getByText("Detailed")).toBeInTheDocument();
    expect(settings.getByText("GPU 1")).toBeInTheDocument();
    expect(settings.getByText("2 min 5 s")).toBeInTheDocument();
  });

  it("shows the review's steps and progress under the paper", async () => {
    mockApi(routes());
    const { pdfInput, serverHas } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");
    expect(screen.queryByLabelText("Review progress")).not.toBeInTheDocument();
    await submitPaper(pdfInput);
    const panel = within(await screen.findByLabelText("Review progress"));

    await serverHas(
      job({
        status: "running",
        position: null,
        steps: ["parse", "figures", "review", "save"],
        step: "figures",
        progress: 40,
        message: "Describing figure 1/3",
      }),
    );
    const state = (label: RegExp) => panel.getByText(label).closest("li")?.dataset.state;
    expect(state(/Parse the PDF/)).toBe("done");
    expect(state(/Describe figures/)).toBe("active");
    expect(state(/Write the review/)).toBe("pending");
    expect(panel.queryByText(/related work/)).not.toBeInTheDocument(); // not in this run's plan
    expect(panel.getByText("Describing figure 1/3")).toBeInTheDocument();
    expect(panel.getByRole("progressbar", { name: "Overall review progress" })).toHaveAttribute("aria-valuenow", "40");

    await serverHas(job({ status: "completed", position: null, progress: 100, review_id: "r1", results }));
    expect(await panel.findByText("Review complete")).toBeInTheDocument();
    expect(state(/Save the review/)).toBe("done");
  });

  it("marks the step that failed and tells the user", async () => {
    mockApi(routes());
    const { pdfInput, serverHas } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");
    await submitPaper(pdfInput);
    await screen.findByLabelText("Review progress");

    await serverHas(job({ status: "running", position: null, step: "review", progress: 50, message: "Reviewing" }));
    await serverHas(job({ status: "failed", position: null, step: "review", progress: 50, message: "Model crashed" }));

    const panel = within(screen.getByLabelText("Review progress"));
    expect(panel.getByText("Review failed")).toBeInTheDocument();
    expect(panel.getByText("Write the review").closest("li")?.dataset.state).toBe("failed");
    expect(panel.getByText("Model crashed")).toBeInTheDocument();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Review Failed", description: "Model crashed" }),
    );
  });

  it("shows reviews already on the server when the page opens, and the whole queue", async () => {
    queue = [
      job({
        id: "theirs",
        owner: "bob",
        filename: "bobs.pdf",
        status: "running",
        position: null,
        gpu: 0,
        progress: 30,
      }),
      job({ id: "mine", owner: "alice", filename: "alices.pdf", status: "queued", position: 1 }),
    ];
    mockApi({ ...routes(), "GET /api/auth/me": { username: "alice", is_admin: false, auth_enabled: true } });
    renderReviewPage();

    const panel = within(await screen.findByLabelText("Review progress"));
    expect(panel.getByText("alices.pdf")).toBeInTheDocument(); // the user's own review, found again
    expect(panel.getByText("Queued: #1 in line")).toBeInTheDocument();

    const list = within(screen.getByRole("list", { name: "Review queue" }));
    const theirs = within(list.getByLabelText("bobs.pdf by bob"));
    expect(theirs.getByText("GPU 0 · 30%")).toBeInTheDocument();
    expect(theirs.queryByRole("button", { name: /Cancel/ })).not.toBeInTheDocument(); // not theirs to cancel
    const mine = within(list.getByLabelText("alices.pdf by alice"));
    expect(mine.getByText("you · llama3:8b")).toBeInTheDocument();
    expect(mine.getByRole("button", { name: "Cancel alices.pdf" })).toBeInTheDocument();

    await userEvent.click(theirs.getByRole("button", { name: "Show bobs.pdf" }));
    expect(panel.getByText("bobs.pdf")).toBeInTheDocument();
  });

  it("cancels a review after confirmation", async () => {
    const api = mockApi(routes());
    vi.spyOn(window, "confirm").mockReturnValue(true);
    queue = [job()];
    renderReviewPage();

    await userEvent.click(await screen.findByRole("button", { name: "Cancel paper.pdf" }));
    await waitFor(() => expect(api.calls("DELETE /api/review-jobs/j1")).toBe(1));
    expect(await screen.findByText("Review cancelled")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dismiss paper.pdf" })).toBeInTheDocument();
  });

  it("sends the chosen review length and generation mode", async () => {
    const api = mockApi(routes());
    const { pdfInput } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");
    await userEvent.selectOptions(screen.getByLabelText("Review Length"), "Detailed");
    await userEvent.selectOptions(screen.getByLabelText("Generation"), "Section by section");
    await submitPaper(pdfInput);

    await waitFor(() => expect(api.calls("POST /api/review-jobs")).toBe(1));
    const [fields = {}] = await api.formFields("POST /api/review-jobs");
    expect(fields.detail).toBe("detailed");
    expect(fields.mode).toBe("sections");
    expect(fields.gpu).toBeUndefined(); // Auto: the first free GPU
  });

  it("starts from the server's default length and mode", async () => {
    mockApi({ ...routes(), "GET /api/config": { max_score: 10, review_detail: "concise", review_mode: "sections" } });
    renderReviewPage();
    await waitFor(() => expect(screen.getByLabelText("Review Length")).toHaveValue("concise"));
    expect(screen.getByLabelText("Generation")).toHaveValue("sections");
  });

  it("searches only the checked related-work sources", async () => {
    const api = mockApi(routes());
    const { pdfInput } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");
    await userEvent.click(screen.getByLabelText("Search arXiv for related work"));
    await submitPaper(pdfInput);

    await waitFor(() => expect(api.calls("POST /api/review-jobs")).toBe(1));
    const [fields = {}] = await api.formFields("POST /api/review-jobs");
    expect(fields.related).toBe("true");
    expect(fields.sources).toBe("semantic_scholar");
  });

  it("can skip the related-work search", async () => {
    const api = mockApi(routes());
    const { pdfInput } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");
    await userEvent.click(screen.getByLabelText("Search arXiv for related work"));
    await userEvent.click(screen.getByLabelText("Search Semantic Scholar for related work"));
    await submitPaper(pdfInput);

    await waitFor(() => expect(api.calls("POST /api/review-jobs")).toBe(1));
    expect((await api.formFields("POST /api/review-jobs"))[0]?.related).toBe("false");
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
      owner: "local",
    };
    let forms: (typeof saved)[] = [];
    let savedName: string | undefined;
    // jsdom's File cannot be parsed back out of a multipart body, so read the text fields from the raw body.
    const field = async (request: Request, name: string) =>
      (await request.text()).match(new RegExp(`name="${name}"\\r\\n\\r\\n([^\\r]*)`))?.[1];
    const api = mockApi({
      ...routes(),
      "GET /api/review-forms": () => ({ forms, count: forms.length }),
      "POST /api/review-forms": async (request: Request) => {
        savedName = await field(request, "name");
        forms = [saved];
        return { ...saved, content: "# Q1" };
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

    await submitPaper(pdfInput);
    await waitFor(() => expect(api.calls("POST /api/review-jobs")).toBe(1));
    expect((await api.formFields("POST /api/review-jobs"))[0]?.review_form_id).toBe(saved.id);
  });

  it("reports a submission the server refuses and keeps the paper", async () => {
    mockApi({
      ...routes(),
      "POST /api/review-jobs": () =>
        new Response(JSON.stringify({ detail: "You already have 10 reviews waiting or running" }), { status: 429 }),
    });
    const { pdfInput } = renderReviewPage();
    await screen.findByLabelText("Select Model for Review");
    await submitPaper(pdfInput);

    await waitFor(() =>
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Upload Failed",
          description: "You already have 10 reviews waiting or running",
        }),
      ),
    );
    expect(screen.getByRole("button", { name: /Start Review/ })).toBeEnabled();
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
