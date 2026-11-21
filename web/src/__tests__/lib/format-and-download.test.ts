import { describe, expect, it, vi } from "vitest";
import { recommendationClassName } from "@/components/RecommendationBadge";
import { saveText } from "@/lib/download";
import { formatBytes } from "@/lib/format";

describe("formatBytes", () => {
  it.each([
    [512, "512 B"],
    [1536, "1.5 KB"],
    [5 * 1024 ** 2, "5.0 MB"],
    [3.5 * 1024 ** 3, "3.50 GB"],
  ])("formats %d as %s", (bytes, expected) => {
    expect(formatBytes(bytes)).toBe(expected);
  });
});

describe("recommendationClassName", () => {
  it("colours by the recommendation's wording", () => {
    expect(recommendationClassName("Accept")).toContain("green");
    expect(recommendationClassName("Strong reject")).toContain("red");
    expect(recommendationClassName("Major Revision")).toContain("yellow");
  });
});

describe("saveText", () => {
  it("downloads the text through a temporary link and cleans up", async () => {
    const createObjectURL = vi.fn((_blob: Blob) => "blob:test");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    saveText("hello", "notes.txt");

    expect(click).toHaveBeenCalledOnce();
    const anchor = click.mock.contexts[0] as HTMLAnchorElement;
    expect(anchor.download).toBe("notes.txt");
    expect(await createObjectURL.mock.calls[0][0].text()).toBe("hello");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:test");
    expect(document.querySelector("a[download]")).toBeNull();
  });
});
