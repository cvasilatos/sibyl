import { useQuery } from "@tanstack/react-query";
import { Check, Copy, Download } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { queries } from "@/lib/api/queries";
import { saveText } from "@/lib/download";
import type { ConferenceSummary } from "@/lib/types";

type Props = {
  conference: ConferenceSummary;
  onClose: () => void;
};

/** Modal showing the plain-text reviewer form of a conference template, as the model receives it. */
export default function ConferenceFormDialog({ conference, onClose }: Props) {
  const { data, error } = useQuery(queries.conference(conference.id));
  const formText = data?.form_markdown ?? null;
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    if (!formText) return;
    await navigator.clipboard.writeText(formText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader className="pr-28">
          <DialogTitle>
            {conference.name} {conference.edition} Review Form
          </DialogTitle>
          <DialogDescription>
            {conference.full_name} · {conference.question_count} questions
            {conference.verified ? "" : " · partly reconstructed from public guidelines"}
          </DialogDescription>
        </DialogHeader>
        <div className="absolute right-12 top-4 flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={copy} disabled={!formText} aria-label="Copy form text">
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => formText && saveText(`${formText}\n`, `review-form-${conference.id}.txt`)}
            disabled={!formText}
            aria-label="Download form as .txt"
          >
            <Download className="h-4 w-4" />
          </Button>
        </div>
        {error ? (
          <p className="text-sm text-destructive">{error.message || "Failed to load the form"}</p>
        ) : formText === null ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner />
            Loading form…
          </div>
        ) : (
          <pre className="max-h-[65vh] overflow-y-auto whitespace-pre-wrap break-words rounded-md bg-muted p-4 font-mono text-xs leading-relaxed">{formText}</pre>
        )}
      </DialogContent>
    </Dialog>
  );
}
