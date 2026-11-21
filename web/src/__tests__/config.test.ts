import { afterEach, describe, expect, it, vi } from "vitest";

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
});
