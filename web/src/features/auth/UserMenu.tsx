"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LogOut, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCurrentUser } from "@/hooks/use-current-user";
import { api } from "@/lib/api";
import { queries } from "@/lib/api/queries";

/** Who is signed in, with a sign-out button (nothing when sign-in is off). */
export default function UserMenu() {
  const user = useCurrentUser();
  const queryClient = useQueryClient();
  const logout = useMutation({
    mutationFn: api.logout,
    onSuccess: () => {
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== "auth" });
      queryClient.setQueryData(queries.currentUser().queryKey, null);
    },
  });
  if (!user?.auth_enabled) return null;
  return (
    <div className="flex items-center gap-2 text-sm">
      <UserRound className="h-4 w-4 text-muted-foreground" aria-hidden />
      <span className="font-medium">{user.username}</span>
      {user.is_admin && <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">admin</span>}
      <Button variant="ghost" size="sm" onClick={() => logout.mutate()} disabled={logout.isPending}>
        <LogOut className="h-4 w-4" />
        Sign Out
      </Button>
    </div>
  );
}
