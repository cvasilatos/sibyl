import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type RenderOptions, render } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

/** A query client for tests: no retries, so a failing request fails the query at once. */
export function testQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
}

export function withQueryClient(client: QueryClient = testQueryClient()) {
  // biome-ignore lint/correctness/noComponentHookFactories: a test wrapper bound to one client, created once per render call.
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

/** Render with a fresh query client (or the given one), returned alongside the render result. */
export function renderWithQuery(
  ui: ReactElement,
  { client = testQueryClient(), ...options }: RenderOptions & { client?: QueryClient } = {},
) {
  return { client, ...render(ui, { wrapper: withQueryClient(client), ...options }) };
}
