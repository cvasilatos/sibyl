import { Check, Copy, Download, Loader2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { ConferenceSummary } from "@/lib/types";

type Props = {
  conference: ConferenceSummary;
  onClose: () => void;
};

/** Modal showing the plain-text reviewer form of a conference template, as the model receives it. */
export default function ConferenceFormDialog({ conference, onClose }: Props) {
  const [formText, setFormText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setFormText(null);
    setError(null);
    api
      .getConference(conference.id, controller.signal)
      .then((data) => setFormText(data.form_markdown))
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Failed to load the form");
      });
    return () => controller.abort();
  }, [conference.id]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const copy = async () => {
    if (!formText) return;
    await navigator.clipboard.writeText(formText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const download = () => {
    if (!formText) return;
    const url = URL.createObjectURL(new Blob([`${formText}\n`], { type: "text/plain;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `review-form-${conference.id}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex w-full items-center justify-center">
      <button type="button" className="absolute inset-0 bg-black/50" aria-label="Close review form dialog" onClick={onClose} />
      <div role="dialog" aria-modal="true" aria-labelledby="conference-form-title" className="relative z-10 bg-background rounded-lg shadow-xl max-w-3xl w-full mx-4 p-6">
        <div className="flex items-start justify-between mb-4 gap-4">
          <div className="min-w-0">
            <h2 id="conference-form-title" className="font-semibold text-lg">
              {conference.name} {conference.edition} Review Form
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              {conference.full_name} · {conference.question_count} questions
              {conference.verified ? "" : " · partly reconstructed from public guidelines"}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button size="sm" variant="outline" onClick={copy} disabled={!formText} aria-label="Copy form text">
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            </Button>
            <Button size="sm" variant="outline" onClick={download} disabled={!formText} aria-label="Download form as .txt">
              <Download className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="outline" onClick={onClose} aria-label="Close">
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : formText === null ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading form…
          </div>
        ) : (
          <pre className="max-h-[65vh] overflow-y-auto whitespace-pre-wrap break-words rounded-md bg-muted p-4 font-mono text-xs leading-relaxed">{formText}</pre>
        )}
      </div>
    </div>
  );
}
