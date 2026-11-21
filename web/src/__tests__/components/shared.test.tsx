import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import NavTabs from "@/components/NavTabs";
import { ErrorAlert } from "@/components/ui/alert";

const pathname = vi.hoisted(() => ({ current: "/library" }));
vi.mock("next/navigation", () => ({ usePathname: () => pathname.current }));

describe("ErrorAlert", () => {
  it("renders nothing without a message", () => {
    const { container } = render(<ErrorAlert>{null}</ErrorAlert>);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the message as an alert", () => {
    render(<ErrorAlert>Boom</ErrorAlert>);
    expect(screen.getByRole("alert")).toHaveTextContent("Boom");
  });
});

describe("NavTabs", () => {
  it("links every page and marks the current one", () => {
    pathname.current = "/library";
    render(<NavTabs />);
    expect(screen.getAllByRole("link").map((link) => link.getAttribute("href"))).toEqual(["/review", "/library", "/models", "/gpu"]);
    expect(screen.getByRole("link", { name: "Library" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Review Paper" })).not.toHaveAttribute("aria-current");
  });
});
