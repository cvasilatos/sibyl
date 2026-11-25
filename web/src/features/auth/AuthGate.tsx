"use client";

import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ErrorAlert } from "@/components/ui/alert";
import { LoadingBlock } from "@/components/ui/spinner";
import { queries } from "@/lib/api/queries";
import LoginForm from "./LoginForm";

/** Show the app to a signed-in user, and the sign-in page to anyone else. */
export default function AuthGate({ children }: { children: ReactNode }) {
  const user = useQuery(queries.currentUser());
  if (user.isPending) return <LoadingBlock label="Loading" className="min-h-screen" />;
  if (user.isError)
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <ErrorAlert>Cannot reach the Sibyl server: {user.error.message}</ErrorAlert>
      </div>
    );
  if (!user.data) return <LoginForm />;
  return children;
}
