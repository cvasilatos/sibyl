"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LogIn } from "lucide-react";
import { type FormEvent, useState } from "react";
import { ErrorAlert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import { queries } from "@/lib/api/queries";

/** Sign in with the username and password of the user's account on the server. */
export default function LoginForm() {
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const login = useMutation({
    mutationFn: () => api.login(username.trim(), password),
    onSuccess: (user) => {
      setPassword("");
      // Data read before signing in (or as someone else) is stale.
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== "auth" });
      queryClient.setQueryData(queries.currentUser().queryKey, user);
    },
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (username.trim() && password) login.mutate();
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <div className="mb-2 flex items-center gap-3">
            <span className="text-3xl" aria-hidden>
              🔮
            </span>
            <CardTitle>
              <h1 className="text-xl font-bold">Sibyl</h1>
            </CardTitle>
          </div>
          <CardDescription>Sign in with your username and password for this server.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1">
              <label htmlFor="login-username" className="text-sm font-medium">
                Username
              </label>
              <Input
                id="login-username"
                autoComplete="username"
                autoFocus
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="login-password" className="text-sm font-medium">
                Password
              </label>
              <Input
                id="login-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
            {login.error && <ErrorAlert>{login.error.message}</ErrorAlert>}
            <Button type="submit" className="w-full" disabled={!username.trim() || !password || login.isPending}>
              {login.isPending ? <Spinner label="Signing in" /> : <LogIn className="h-4 w-4" />}
              Sign In
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
