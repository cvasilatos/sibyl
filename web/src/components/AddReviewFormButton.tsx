"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { invalidates } from "@/lib/api/queries";
import { reviewFormProblem, suggestedFormName } from "@/lib/review-forms";
import type { SavedFormDetail } from "@/lib/types";

type Props = {
  onSaved?: (form: SavedFormDetail) => void;
  disabled?: boolean;
  className?: string;
  label?: string;
};

/** Uploads a TXT or Markdown reviewer form and asks for a name, so the form is saved and can be picked again later. */
export default function AddReviewFormButton({ onSaved, disabled = false, className, label = "Upload Review Form" }: Props) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");

  const save = useMutation({
    mutationFn: ({ name, file }: { name: string; file: File }) => api.saveReviewForm(name, file),
    onSuccess: async (form) => {
      await queryClient.invalidateQueries(invalidates.reviewForms);
      setFile(null);
      toast({ title: "Review Form Saved", description: `"${form.name}" is now in your review forms.` });
      onSaved?.(form);
    },
  });

  const close = () => {
    setFile(null);
    save.reset();
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        aria-label="Review form file"
        accept=".txt,.md,.markdown,text/plain,text/markdown"
        className="hidden"
        disabled={disabled}
        onChange={(event) => {
          const chosen = event.target.files?.[0];
          event.target.value = ""; // so choosing the same file again still fires onChange
          if (!chosen) return;
          const problem = reviewFormProblem(chosen);
          if (problem) {
            toast({ title: "Invalid Review Form", description: problem, variant: "destructive" });
            return;
          }
          setName(suggestedFormName(chosen));
          setFile(chosen);
        }}
      />
      <Button type="button" variant="outline" className={className} onClick={() => inputRef.current?.click()} disabled={disabled}>
        <FileUp className="mr-2 h-4 w-4" />
        {label}
      </Button>

      {file && (
        <Dialog open onOpenChange={(open) => !open && close()}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Name This Review Form</DialogTitle>
              <DialogDescription>Saved forms appear in the Review Forms tab and in the review form list, so you can reuse them.</DialogDescription>
            </DialogHeader>
            <form
              className="mt-4 space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                if (name.trim()) save.mutate({ name: name.trim(), file });
              }}
            >
              <div className="space-y-2">
                <label htmlFor="review-form-name" className="text-sm font-medium">
                  Name
                </label>
                <Input id="review-form-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={100} autoFocus placeholder="e.g. Workshop on Efficient ML 2026" />
                <p className="truncate text-xs text-muted-foreground" title={file.name}>
                  From {file.name}
                </p>
                {save.error && <p className="text-sm text-destructive">{save.error.message}</p>}
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={close} disabled={save.isPending}>
                  Cancel
                </Button>
                <Button type="submit" disabled={!name.trim() || save.isPending}>
                  {save.isPending && <Spinner className="mr-2" label="Saving" />}
                  Save Form
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
