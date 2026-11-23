import { defineConfig, devices } from "@playwright/test";

// End-to-end tests start their own backend and web app on separate ports, so they never collide with dev servers.
const API_PORT = 18000;
const WEB_PORT = 13000;
const apiUrl = `http://localhost:${API_PORT}`;
const webUrl = `http://localhost:${WEB_PORT}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: { baseURL: webUrl, trace: "on-first-retry" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `uv run --directory ../backend uvicorn sibyl.main:app --port ${API_PORT}`,
      url: `${apiUrl}/`,
      reuseExistingServer: !process.env.CI,
    },
    {
      // NEXT_PUBLIC_API_URL is baked in at build time, so CI builds with it before starting.
      command: process.env.CI
        ? `npm run build && npm run start -- --port ${WEB_PORT}`
        : `npm run dev -- --port ${WEB_PORT}`,
      url: webUrl,
      env: { NEXT_PUBLIC_API_URL: apiUrl },
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
  ],
});
