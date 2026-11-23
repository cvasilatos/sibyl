"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, Copy, Download, Play } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { queries } from "@/lib/api/queries";
import { saveText } from "@/lib/download";
import { pageLimitText } from "@/lib/page-limit";
import type { FormRef } from "@/lib/review-forms";
import type { ConferenceSummary, SavedFormSummary } from "@/lib/types";

type Props = {
  form: FormRef;
  conference?: ConferenceSummary;
  savedForm?: SavedFormSummary;
  onUse?: () => void;
};

function useFormText(form: FormRef): { text: string | null; error: Error | null } {
  const conference = useQuery({ ...queries.conference(form.id), enabled: form.kind === "conference" });
  const saved = useQuery({ ...queries.reviewForm(form.id), enabled: form.kind === "custom" });
  return form.kind === "conference"
    ? { text: conference.data?.form_markdown ?? null, error: conference.error }
    : { text: saved.data?.content ?? null, error: saved.error };
}

/** The text of a reviewer form, as the model receives it, with copy, download and "use for a review". */
export default function FormViewer({ form, conference, savedForm, onUse }: Props) {
  const { text, error } = useFormText(form);
  const [copied, setCopied] = useState(false);

  const title = conference
    ? `${conference.name} ${conference.edition} Review Form`
    : (savedForm?.name ?? "Review Form");
  const details = conference
    ? [
        conference.full_name,
        `${conference.question_count} questions`,
        conference.page_limit ? pageLimitText(conference.page_limit) : null,
        conference.verified ? null : "partly reconstructed from public guidelines",
      ]
    : savedForm
      ? ["Your form", `from ${savedForm.filename}`, `added ${new Date(savedForm.created_at).toLocaleDateString()}`]
      : [];

  const copy = async () => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section aria-label={title} className="space-y-3 rounded-lg border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold">{title}</h2>
          <p className="text-sm text-muted-foreground">{details.filter(Boolean).join(" · ")}</p>
          {conference?.source_urls.length ? (
            <p className="mt-1 flex flex-wrap gap-x-3 text-xs">
              {conference.source_urls.map((url) => (
                <a
                  key={url}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="truncate text-primary underline underline-offset-2 hover:no-underline"
                >
                  {new URL(url).hostname}
                </a>
              ))}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={copy} disabled={!text} aria-label="Copy form text">
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => text && saveText(`${text}\n`, `review-form-${form.id}.txt`)}
            disabled={!text}
            aria-label="Download form as .txt"
          >
            <Download className="h-4 w-4" />
          </Button>
          {onUse && (
            <Button size="sm" onClick={onUse}>
              <Play className="mr-2 h-4 w-4" />
              Use for a Review
            </Button>
          )}
        </div>
      </div>
      {error ? (
        <p className="text-sm text-destructive">{error.message || "Failed to load the form"}</p>
      ) : text === null ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner />
          Loading form…
        </div>
      ) : (
        <pre className="max-h-[70vh] overflow-y-auto whitespace-pre-wrap break-words rounded-md bg-muted p-4 font-mono text-xs leading-relaxed">
          {text}
        </pre>
      )}
    </section>
  );
}
