import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import AuthGate from "@/features/auth/AuthGate";
import UserMenu from "@/features/auth/UserMenu";
import { createQueryClient } from "@/lib/api/queries";
import { mockApi } from "../../helpers/fetch";
import { renderWithQuery } from "../../helpers/render";

const unauthorized = () => new Response(JSON.stringify({ detail: "Sign in to use Sibyl" }), { status: 401 });
const alice = { username: "alice", is_admin: false, auth_enabled: true };

function renderApp() {
  return renderWithQuery(
    <AuthGate>
      <UserMenu />
      <p>The app</p>
    </AuthGate>,
    { client: createQueryClient() },
  );
}

describe("sign-in", () => {
  it("shows the sign-in page until the user signs in with their server account", async () => {
    let signedIn = false;
    let sent: unknown;
    const api = mockApi({
      "GET /api/auth/me": () => (signedIn ? alice : unauthorized()),
      "POST /api/auth/login": async (request: Request) => {
        sent = await request.json();
        signedIn = true;
        return alice;
      },
    });
    renderApp();

    await userEvent.type(await screen.findByLabelText("Username"), " alice ");
    await userEvent.type(screen.getByLabelText("Password"), "s3cret");
    expect(screen.queryByText("The app")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(await screen.findByText("The app")).toBeInTheDocument();
    expect(sent).toEqual({ username: "alice", password: "s3cret" });
    expect(screen.getByText("alice")).toBeInTheDocument();
    expect(api.requests.every((request) => request.credentials === "include")).toBe(true);
  });

  it("shows why a sign-in failed", async () => {
    mockApi({
      "GET /api/auth/me": unauthorized,
      "POST /api/auth/login": () =>
        new Response(JSON.stringify({ detail: "Wrong username or password" }), { status: 401 }),
    });
    renderApp();
    await userEvent.type(await screen.findByLabelText("Username"), "alice");
    await userEvent.type(screen.getByLabelText("Password"), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));
    expect(await screen.findByText("Wrong username or password")).toBeInTheDocument();
  });

  it("returns to the sign-in page when the session expires or the user signs out", async () => {
    let signedIn = true;
    const api = mockApi({
      "GET /api/auth/me": () => (signedIn ? alice : unauthorized()),
      "GET /api/reviews": unauthorized,
      "POST /api/auth/logout": () => {
        signedIn = false;
        return { message: "Signed out" };
      },
    });
    const { client } = renderApp();
    expect(await screen.findByText("The app")).toBeInTheDocument();

    // Any request answered 401 (the sign-in expired) brings the sign-in page back.
    await act(() =>
      client
        .fetchQuery({
          queryKey: ["reviews"],
          queryFn: async () => {
            const { api: backend } = await import("@/lib/api");
            return backend.listReviews();
          },
        })
        .catch(() => undefined),
    );
    expect(await screen.findByLabelText("Username")).toBeInTheDocument();

    signedIn = true;
    await act(() => client.invalidateQueries({ queryKey: ["auth"] }));
    expect(await screen.findByText("The app")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sign Out" }));
    await waitFor(() => expect(api.calls("POST /api/auth/logout")).toBe(1));
    expect(await screen.findByLabelText("Username")).toBeInTheDocument();
  });

  it("shows no user menu when sign-in is off", async () => {
    mockApi({});
    renderApp();
    expect(await screen.findByText("The app")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign Out" })).not.toBeInTheDocument();
  });
});
