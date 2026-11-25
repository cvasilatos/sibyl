import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import ReviewFormsBrowser from "@/features/forms/ReviewFormsBrowser";
import { mockApi } from "../../helpers/fetch";
import { renderWithQuery } from "../../helpers/render";

vi.mock("@/hooks/use-toast", () => ({
  toast: vi.fn(),
  useToast: () => ({ toast: vi.fn(), toasts: [], dismiss: vi.fn() }),
}));

const neurips = {
  id: "neurips",
  name: "NeurIPS",
  full_name: "Neural Information Processing Systems",
  area: "Machine Learning",
  edition: "2026",
  verified: true,
  source_urls: ["https://neurips.cc/guidelines"],
  question_count: 9,
  page_limit: null,
};
const saved = {
  id: "b".repeat(32),
  name: "Lab Template",
  filename: "lab.md",
  created_at: "2026-11-01T00:00:00Z",
  size: 10,
  owner: "alice",
};

function Browser({ onUse }: { onUse?: (key: string) => void }) {
  const [key, setKey] = useState<string | null>(null);
  return <ReviewFormsBrowser selectedKey={key} onSelect={setKey} onUse={onUse} />;
}

describe("ReviewFormsBrowser", () => {
  it("lists saved and conference forms and shows the chosen form's text inline", async () => {
    mockApi({
      "GET /api/conferences": { conferences: [neurips], count: 1 },
      "GET /api/conferences/neurips": { ...neurips, questions: [], form_markdown: "# NeurIPS 2026 reviewer form" },
      "GET /api/review-forms": { forms: [saved], count: 1 },
      [`GET /api/review-forms/${saved.id}`]: { ...saved, content: "## Strengths" },
    });
    const onUse = vi.fn();
    renderWithQuery(<Browser onUse={onUse} />);

    expect(await screen.findByText("Choose a form to read it, or add your own.")).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: "NeurIPS 2026" }));
    expect(await screen.findByText("# NeurIPS 2026 reviewer form")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Lab Template" }));
    expect(await screen.findByText("## Strengths")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Use for a Review/ }));
    expect(onUse).toHaveBeenCalledWith(`custom:${saved.id}`);
  });

  it("deletes a saved form after confirmation", async () => {
    let forms = [saved];
    const api = mockApi({
      "GET /api/conferences": { conferences: [], count: 0 },
      "GET /api/review-forms": () => ({ forms, count: forms.length }),
      [`DELETE /api/review-forms/${saved.id}`]: () => {
        forms = [];
        return { message: "Review form deleted", id: saved.id };
      },
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderWithQuery(<Browser />);

    await userEvent.click(await screen.findByRole("button", { name: "Delete Lab Template" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Lab Template" })).not.toBeInTheDocument());
    expect(api.calls(`DELETE /api/review-forms/${saved.id}`)).toBe(1);
    expect(screen.getByText("No saved forms yet.")).toBeInTheDocument();
  });

  it("offers to delete only the user's own forms", async () => {
    mockApi({
      "GET /api/auth/me": { username: "bob", is_admin: false, auth_enabled: true },
      "GET /api/conferences": { conferences: [], count: 0 },
      "GET /api/review-forms": { forms: [saved], count: 1 },
    });
    renderWithQuery(<Browser />);
    expect(await screen.findByText("Lab Template")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete Lab Template" })).not.toBeInTheDocument();
  });
});
