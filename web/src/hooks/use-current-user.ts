"use client";

import { useQuery } from "@tanstack/react-query";
import { queries } from "@/lib/api/queries";
import type { CurrentUser } from "@/lib/types";

/** The signed-in user (null while loading or signed out). */
export function useCurrentUser(): CurrentUser | null {
  return useQuery(queries.currentUser()).data ?? null;
}

/** Whether the signed-in user may delete or cancel something `owner` made (null: made before Sibyl had users). */
export function canManage(user: CurrentUser | null, owner: string | null | undefined): boolean {
  if (!user) return false;
  return user.is_admin || (owner != null && owner === user.username);
}

/** Like `canManage`, for the signed-in user. */
export function useCanManage(): (owner: string | null | undefined) => boolean {
  const user = useCurrentUser();
  return (owner) => canManage(user, owner);
}
