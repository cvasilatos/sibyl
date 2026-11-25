import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DownloadProvider } from "@/features/models/download-context";
import ModelManager from "@/features/models/ModelManager";
import { mockApi } from "../../helpers/fetch";
import { renderWithQuery } from "../../helpers/render";
import { FakeWebSocket, installFakeWebSocket } from "../../helpers/websocket";

const toast = vi.hoisted(() => vi.fn(() => ({ id: "t", dismiss: vi.fn(), update: vi.fn() })));
vi.mock("@/hooks/use-toast", () => ({ toast, useToast: () => ({ toast, toasts: [], dismiss: vi.fn() }) }));

function routes(installed: string[] = []) {
  return {
    "GET /api/engine": {
      name: "ollama",
      label: "Ollama",
      supports_downloads: true,
      platform: "linux",
      machine: "x86_64",
    },
    "GET /api/models": () => ({
      models: installed.map((model) => ({ model, size: 5 * 1024 ** 3, digest: model, modified_at: "2026-01-01" })),
    }),
    "GET /api/models/available": {
      models: [{ name: "qwen3", description: "Qwen 3", size: "5 GB", installed: false, installed_variants: [] }],
    },
    "GET /api/models/available/qwen3/tags": { model: "qwen3", tags: ["8b", "14b"] },
  };
}

function renderManager() {
  return renderWithQuery(
    <DownloadProvider>
      <ModelManager />
    </DownloadProvider>,
  );
}

describe("ModelManager", () => {
  beforeEach(() => {
    installFakeWebSocket();
    toast.mockClear();
  });

  it("installs the chosen variant and refreshes the installed list when done", async () => {
    const installed: string[] = [];
    const api = mockApi(routes(installed));
    renderManager();
    expect(await screen.findByText("No models installed. Install one from above.")).toBeInTheDocument();

    await userEvent.click(await screen.findByRole("button", { name: /Install/ }));
    await userEvent.selectOptions(await screen.findByLabelText("Variant of qwen3"), "14b");
    await userEvent.click(screen.getByRole("button", { name: /Confirm/ }));

    const socket = FakeWebSocket.last();
    expect(new URL(socket.url).searchParams.get("model_name")).toBe("qwen3:14b");
    act(() => socket.receive({ status: "pulling", completed: 50, total: 100 }));
    installed.push("qwen3:14b");
    act(() => socket.receive({ status: "success", completed: 100, total: 100 }));

    expect(await screen.findByText("qwen3:14b")).toBeInTheDocument();
    expect(api.calls("GET /api/models")).toBe(2);
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ title: "Installation Complete" }));
  });

  it("shows a failed install", async () => {
    mockApi(routes());
    renderManager();
    await userEvent.click(await screen.findByRole("button", { name: /Install/ }));
    await userEvent.click(await screen.findByRole("button", { name: /Confirm/ }));

    act(() => FakeWebSocket.last().receive({ status: "error", message: "Disk full" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Disk full");
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Installation Failed", description: "Disk full" }),
    );
  });

  it("deletes an installed model after confirmation", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const installed = ["qwen3:8b"];
    const api = mockApi({
      ...routes(installed),
      "DELETE /api/models/qwen3:8b": () => {
        installed.length = 0;
        return { message: "deleted" };
      },
    });
    renderManager();
    await userEvent.click(await screen.findByRole("button", { name: "Delete qwen3:8b" }));

    await waitFor(() => expect(screen.queryByText("qwen3:8b")).not.toBeInTheDocument());
    expect(api.calls("DELETE /api/models/qwen3:8b")).toBe(1);
  });

  it("hides the catalog when the engine cannot download models", async () => {
    mockApi({
      ...routes(),
      "GET /api/engine": {
        name: "openai",
        label: "OpenAI-compatible",
        supports_downloads: false,
        platform: "linux",
        machine: "x86_64",
      },
    });
    renderManager();
    expect(await screen.findByText(/Models are managed by your inference server/)).toBeInTheDocument();
    expect(screen.queryByText("Browse & Install Models")).not.toBeInTheDocument();
  });

  it("lets only admins delete models", async () => {
    mockApi({ ...routes(["qwen3:8b"]), "GET /api/auth/me": { username: "bob", is_admin: false, auth_enabled: true } });
    renderManager();
    expect(await screen.findByText("qwen3:8b")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete qwen3:8b" })).not.toBeInTheDocument();
  });
});
