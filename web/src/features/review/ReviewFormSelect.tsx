"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import AddReviewFormButton from "@/components/AddReviewFormButton";
import { NativeSelect } from "@/components/ui/native-select";
import { queries } from "@/lib/api/queries";
import { groupByArea } from "@/lib/conferences";
import { conferenceOptionLabel, pageLimitText } from "@/lib/page-limit";
import { formKey, parseFormKey } from "@/lib/review-forms";
import { useReview } from "./review-context";

const linkClass = "text-primary underline underline-offset-2 hover:no-underline";

/** Picks the reviewer form to answer: a conference template or one of the user's saved forms. Uploading a new form saves it under a name. */
export default function ReviewFormSelect() {
  const { selectedFormKey, selectForm, isReviewing } = useReview();
  const { data: conferences = [] } = useQuery(queries.conferences());
  const { data: savedForms = [] } = useQuery(queries.reviewForms());
  const selected = parseFormKey(selectedFormKey);
  const conference = selected?.kind === "conference" ? conferences.find((c) => c.id === selected.id) : undefined;
  const savedForm = selected?.kind === "custom" ? savedForms.find((f) => f.id === selected.id) : undefined;

  return (
    <div className="space-y-2">
      <label htmlFor="review-form-select" className="text-sm font-medium">
        Review Form
      </label>
      <NativeSelect id="review-form-select" value={selectedFormKey ?? ""} onChange={(e) => selectForm(e.target.value || null)} disabled={isReviewing}>
        <option value="">Generic Sibyl review</option>
        {savedForms.length > 0 && (
          <optgroup label="Your forms">
            {savedForms.map((form) => (
              <option key={form.id} value={formKey({ kind: "custom", id: form.id })}>
                {form.name}
              </option>
            ))}
          </optgroup>
        )}
        {groupByArea(conferences).map(([area, items]) => (
          <optgroup key={area} label={area}>
            {items.map((c) => (
              <option key={c.id} value={formKey({ kind: "conference", id: c.id })}>
                {conferenceOptionLabel(c)}
              </option>
            ))}
          </optgroup>
        ))}
      </NativeSelect>
      <p className="text-xs text-muted-foreground">
        {conference
          ? `${conference.full_name}: the model answers all ${conference.question_count} questions of the official reviewer form.${conference.verified ? "" : " Form partly reconstructed from public guidelines."}`
          : savedForm
            ? `Your form "${savedForm.name}": the model completes its sections.`
            : "Answer a conference's official reviewer form, or one of your own."}
        {conference?.page_limit && (
          <>
            {" "}
            Page limit: {pageLimitText(conference.page_limit)} (
            <a href={conference.page_limit.source_url} target="_blank" rel="noopener noreferrer" className={linkClass}>
              {conference.name} {conference.page_limit.edition} call for papers
            </a>
            ).
          </>
        )}{" "}
        <Link href={selectedFormKey ? `/forms?form=${encodeURIComponent(selectedFormKey)}` : "/forms"} className={linkClass}>
          {selectedFormKey ? "View form" : "Browse forms"}
        </Link>
      </p>
      <AddReviewFormButton className="w-full" disabled={isReviewing} onSaved={(form) => selectForm(formKey({ kind: "custom", id: form.id }))} />
      <p className="text-xs text-muted-foreground">TXT or Markdown, up to 64 KiB. You name it once and can pick it again later.</p>
    </div>
  );
}
