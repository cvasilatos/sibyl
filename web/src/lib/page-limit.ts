import type { ConferenceSummary } from "@/lib/types";

type PageLimit = NonNullable<ConferenceSummary["page_limit"]>;

/** Full wording, e.g. "6 pages, excluding references". */
export function pageLimitText(limit: PageLimit): string {
  const excludes = limit.excludes ? `, excluding ${limit.excludes}` : "";
  const note = limit.note ? `; ${limit.note}` : "";
  return `${limit.pages} pages${excludes}${note}`;
}

/** Dropdown label, e.g. "DAC 2026 · 6 pages". */
export function conferenceOptionLabel(conference: ConferenceSummary): string {
  const base = `${conference.name} ${conference.edition}`;
  return conference.page_limit ? `${base} · ${conference.page_limit.pages} pages` : base;
}
