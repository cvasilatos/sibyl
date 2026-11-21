"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { NativeSelect } from "@/components/ui/native-select";
import { queries } from "@/lib/api/queries";
import type { ConferenceSummary } from "@/lib/types";
import ConferenceFormDialog from "./ConferenceFormDialog";
import { useReview } from "./review-context";

function groupByArea(conferences: ConferenceSummary[]): [string, ConferenceSummary[]][] {
  const groups = new Map<string, ConferenceSummary[]>();
  for (const conference of conferences) groups.set(conference.area, [...(groups.get(conference.area) ?? []), conference]);
  return [...groups.entries()];
}

/** Picks a conference reviewer form, and previews it when picked. */
export default function ConferenceSelect() {
  const { selectedConferenceId, selectConference, isReviewing } = useReview();
  const { data: conferences = [] } = useQuery(queries.conferences());
  const byArea = useMemo(() => groupByArea(conferences), [conferences]);
  const selected = conferences.find((c) => c.id === selectedConferenceId) ?? null;
  const [showForm, setShowForm] = useState(false);

  if (conferences.length === 0) return null;
  return (
    <div className="space-y-2">
      <label htmlFor="conference-select" className="text-sm font-medium">
        Conference Review Template
      </label>
      <NativeSelect
        id="conference-select"
        value={selectedConferenceId ?? ""}
        onChange={(e) => {
          selectConference(e.target.value || null);
          setShowForm(Boolean(e.target.value));
        }}
        disabled={isReviewing}
      >
        <option value="">Generic Sibyl review</option>
        {byArea.map(([area, items]) => (
          <optgroup key={area} label={area}>
            {items.map((conference) => (
              <option key={conference.id} value={conference.id}>
                {conference.name} {conference.edition}
              </option>
            ))}
          </optgroup>
        ))}
      </NativeSelect>
      <p className="text-xs text-muted-foreground">
        {selected
          ? `${selected.full_name}: the model answers all ${selected.question_count} questions of the official reviewer form.${selected.verified ? "" : " Form partly reconstructed from public guidelines."}`
          : "Answer a top conference's official reviewer form, with its own score scales."}
        {selected && (
          <>
            {" "}
            <button type="button" className="text-primary underline underline-offset-2 hover:no-underline" onClick={() => setShowForm(true)}>
              View form
            </button>
          </>
        )}
      </p>
      {showForm && selected && <ConferenceFormDialog conference={selected} onClose={() => setShowForm(false)} />}
    </div>
  );
}
