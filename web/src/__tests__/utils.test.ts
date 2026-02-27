import { describe, expect, it } from "vitest";
import { cn } from "@/lib/utils";

describe("cn", () => {
  it("returns a single class name unchanged", () => {
    expect(cn("foo")).toBe("foo");
  });

  it("merges multiple class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("handles conditional classes (falsy values ignored)", () => {
    expect(cn("a", false && "b", "c")).toBe("a c");
    expect(cn("a", undefined, "c")).toBe("a c");
    expect(cn("a", null, "c")).toBe("a c");
  });

  it("deduplicates conflicting Tailwind classes (last wins)", () => {
    // tailwind-merge removes the first conflicting utility
    expect(cn("p-4", "p-8")).toBe("p-8");
  });

  it("handles object syntax from clsx", () => {
    expect(cn({ active: true, disabled: false })).toBe("active");
  });

  it("handles array syntax from clsx", () => {
    expect(cn(["foo", "bar"])).toBe("foo bar");
  });

  it("returns empty string when no arguments provided", () => {
    expect(cn()).toBe("");
  });

  it("merges Tailwind color utilities correctly", () => {
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
  });
});
