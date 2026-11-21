import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns the parsed body", async () => {
    const stats = { total_reviews: 2, unique_papers: 1, unique_models: 2, recommendations: { Accept: 2 } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(stats)));
    await expect(api.getStatistics()).resolves.toEqual(stats);
  });

  it("throws the backend's detail message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Review not found" }, 404)));
    await expect(api.getReview("missing")).rejects.toThrow("Review not found");
  });

  it("falls back to the status when there is no detail", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("oops", { status: 502 })));
    await expect(api.listGpus()).rejects.toThrow("Request failed with status 502");
  });

  it("encodes path parameters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ model: "Qwen/Qwen3-8B", tags: [] }));
    vi.stubGlobal("fetch", fetchMock);
    await api.listModelTags("Qwen/Qwen3-8B");
    const request: Request = fetchMock.mock.calls[0]?.[0];
    expect(request.url).toContain("/api/models/available/Qwen%2FQwen3-8B/tags");
  });
});
