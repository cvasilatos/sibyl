import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// We import after each env setup so the module picks up the right value.
describe("config module", () => {
  describe("API_URL", () => {
    it("defaults to http://localhost:8000 when env var is not set", async () => {
      vi.stubEnv("NEXT_PUBLIC_API_URL", "");
      const { API_URL } = await import("@/lib/config");
      // When env var is empty string falsy, default is used
      expect(API_URL).toBe("http://localhost:8000");
    });

    it("uses the env var value when set", async () => {
      vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com");
      vi.resetModules();
      const { API_URL } = await import("@/lib/config");
      expect(API_URL).toBe("https://api.example.com");
    });
  });

  describe("getWebSocketUrl", () => {
    afterEach(() => {
      vi.unstubAllEnvs();
      vi.resetModules();
    });

    it("converts http:// to ws://", async () => {
      vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
      vi.resetModules();
      const { getWebSocketUrl } = await import("@/lib/config");
      expect(getWebSocketUrl()).toBe("ws://localhost:8000");
    });

    it("converts https:// to wss://", async () => {
      vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com");
      vi.resetModules();
      const { getWebSocketUrl } = await import("@/lib/config");
      expect(getWebSocketUrl()).toBe("wss://api.example.com");
    });
  });

  describe("fetchMaxScore", () => {
    beforeEach(() => {
      vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
      vi.resetModules();
    });

    afterEach(() => {
      vi.unstubAllEnvs();
      vi.resetModules();
    });

    it("returns parsed max_score on success", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ max_score: 5 }),
      } as Response);

      const { fetchMaxScore } = await import("@/lib/config");
      const score = await fetchMaxScore();
      expect(score).toBe(5);
    });

    it("throws when fetch fails (not ok)", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({}),
      } as Response);

      const { fetchMaxScore } = await import("@/lib/config");
      await expect(fetchMaxScore()).rejects.toThrow("Failed to fetch config");
    });

    it("throws when max_score is not a number", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ max_score: "five" }),
      } as Response);

      const { fetchMaxScore } = await import("@/lib/config");
      await expect(fetchMaxScore()).rejects.toThrow("Invalid max_score");
    });

    it("throws when max_score is zero or negative", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ max_score: 0 }),
      } as Response);

      const { fetchMaxScore } = await import("@/lib/config");
      await expect(fetchMaxScore()).rejects.toThrow("Invalid max_score");
    });
  });
});
