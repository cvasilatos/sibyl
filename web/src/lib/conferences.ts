import type { ConferenceSummary } from "@/lib/types";

/** Conferences grouped by research area, keeping the backend's order (areas, then names). */
export function groupByArea(conferences: ConferenceSummary[]): [string, ConferenceSummary[]][] {
  const groups = new Map<string, ConferenceSummary[]>();
  for (const conference of conferences)
    groups.set(conference.area, [...(groups.get(conference.area) ?? []), conference]);
  return [...groups.entries()];
}
