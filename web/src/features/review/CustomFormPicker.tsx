"use client";

import { FileText, FileUp, X } from "lucide-react";
import { useRef } from "react";
import { Button } from "@/components/ui/button";
import { useReview } from "./review-context";

/** Upload of a custom TXT or Markdown reviewer form, as an alternative to a conference template. */
export default function CustomFormPicker() {
  const { selectedReviewForm, selectReviewForm, conferences, isReviewing } = useReview();
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="space-y-2">
      <label htmlFor="review-form-input" className="text-sm font-medium">
        {conferences.length > 0 ? "Or Upload a Custom Form" : "Review Form (Optional)"}
      </label>
      <input
        ref={inputRef}
        id="review-form-input"
        type="file"
        accept=".txt,.md,.markdown,text/plain,text/markdown"
        className="hidden"
        disabled={isReviewing}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) selectReviewForm(file);
          event.target.value = ""; // so choosing the same file again still fires onChange
        }}
      />
      {selectedReviewForm ? (
        <div className="flex items-center gap-2 rounded-md border border-input px-3 py-2">
          <FileText className="h-4 w-4 shrink-0 text-primary" />
          <span className="min-w-0 flex-1 truncate text-sm" title={selectedReviewForm.name}>
            {selectedReviewForm.name}
          </span>
          <Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => selectReviewForm(null)} disabled={isReviewing} aria-label="Remove review form">
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <Button type="button" variant="outline" className="w-full" onClick={() => inputRef.current?.click()} disabled={isReviewing}>
          <FileUp className="mr-2 h-4 w-4" />
          Upload Review Form
        </Button>
      )}
      <p className="text-xs text-muted-foreground">TXT or Markdown, up to 64 KiB. The model will complete its sections.</p>
    </div>
  );
}
