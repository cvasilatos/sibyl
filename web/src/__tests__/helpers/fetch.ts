import { vi } from "vitest";

type Handler = unknown | ((request: Request) => unknown | Response | Promise<unknown | Response>);

/**
 * Stub global fetch with handlers keyed by "METHOD /path" (query string ignored). A handler is a JSON body, a
 * Response, or a function returning either. Unknown routes answer 404. `calls(route)` counts requests to a route.
 */
export function mockApi(routes: Record<string, Handler>) {
  const requests: Request[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = input instanceof Request ? input : new Request(input, init);
    requests.push(request);
    const key = `${request.method} ${decodeURIComponent(new URL(request.url).pathname)}`;
    if (!(key in routes)) return new Response(JSON.stringify({ detail: `No mock for ${key}` }), { status: 404 });
    const handler = routes[key];
    const result = typeof handler === "function" ? await handler(request) : handler;
    return result instanceof Response
      ? result
      : new Response(JSON.stringify(result), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return {
    requests,
    calls: (route: string) =>
      requests.filter((r) => `${r.method} ${decodeURIComponent(new URL(r.url).pathname)}` === route).length,
  };
}
