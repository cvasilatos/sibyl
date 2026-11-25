import { vi } from "vitest";

type Handler = unknown | ((request: Request) => unknown | Response | Promise<unknown | Response>);

/** The user `mockApi` signs in unless a test gives its own "GET /api/auth/me": the admin of an install without sign-in. */
export const LOCAL_USER = { username: "local", is_admin: true, auth_enabled: false };

/**
 * Stub global fetch with handlers keyed by "METHOD /path" (query string ignored). A handler is a JSON body, a
 * Response, or a function returning either. Unknown routes answer 404. `calls(route)` counts requests to a route.
 */
export function mockApi(givenRoutes: Record<string, Handler>) {
  const routes: Record<string, Handler> = { "GET /api/auth/me": LOCAL_USER, ...givenRoutes };
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
    /** The text fields of each multipart request to a route (files are left out). */
    async formFields(route: string): Promise<Record<string, string>[]> {
      const matching = requests.filter((r) => `${r.method} ${decodeURIComponent(new URL(r.url).pathname)}` === route);
      // jsdom's File cannot be parsed back out of a multipart body, so read the text fields from the raw body.
      return Promise.all(
        matching.map(async (request) => {
          const body = await request.clone().text();
          const fields: Record<string, string> = {};
          for (const [, name = "", value = ""] of body.matchAll(/name="([^"]+)"\r\n\r\n([^\r]*)/g))
            fields[name] = value;
          return fields;
        }),
      );
    },
    calls: (route: string) =>
      requests.filter((r) => `${r.method} ${decodeURIComponent(new URL(r.url).pathname)}` === route).length,
  };
}
