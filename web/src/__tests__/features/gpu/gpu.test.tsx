import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import GpuLoadSummary from "@/features/gpu/GpuLoadSummary";
import GpuMonitor from "@/features/gpu/GpuMonitor";
import { mockApi } from "../../helpers/fetch";
import { renderWithQuery } from "../../helpers/render";

const gpu = {
  index: 0,
  name: "RTX 4090",
  gpu_utilization: 42,
  memory_used: 8 * 1024 ** 3,
  memory_total: 24 * 1024 ** 3,
  memory_free: 16 * 1024 ** 3,
  temperature: 60,
  power_usage_watts: 200,
  power_limit_watts: 450,
  fan_speed_percent: 30,
  processes: [],
};

describe("GPU views", () => {
  it("share one /api/gpu request when shown together", async () => {
    const api = mockApi({ "GET /api/gpu": { available: true, count: 1, gpus: [gpu] } });
    renderWithQuery(
      <>
        <GpuMonitor />
        <GpuLoadSummary />
      </>
    );
    expect(await screen.findByText("RTX 4090")).toBeInTheDocument();
    expect(screen.getByText("VRAM")).toBeInTheDocument(); // only the summary has it
    expect(api.calls("GET /api/gpu")).toBe(1);
  });

  it("explains when there is no NVIDIA GPU", async () => {
    mockApi({ "GET /api/gpu": { available: false, count: 0, gpus: [] } });
    renderWithQuery(<GpuMonitor />);
    expect(await screen.findByText("No NVIDIA GPU detected.")).toBeInTheDocument();
  });

  it("shows the request error", async () => {
    mockApi({ "GET /api/gpu": new Response(JSON.stringify({ detail: "NVML failed" }), { status: 500 }) });
    renderWithQuery(<GpuMonitor />);
    expect(await screen.findByRole("alert")).toHaveTextContent("NVML failed");
  });
});
