"use client";

import { FileText } from "lucide-react";
import { type DragEvent, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { useReview } from "./review-context";

/** Click or drop target for the paper PDF. */
export default function PaperDropzone() {
  const { selectedFile, selectFile, isSubmitting } = useReview();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const onDragOver = (event: DragEvent) => {
    event.preventDefault();
    setIsDragging(true);
  };
  const onDragLeave = (event: DragEvent) => {
    event.preventDefault();
    setIsDragging(false);
  };
  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file && !isSubmitting) selectFile(file);
  };

  return (
    <button
      type="button"
      disabled={isSubmitting}
      className={cn(
        "w-full cursor-pointer rounded-lg border-2 border-dashed p-12 text-center transition-all disabled:cursor-not-allowed",
        isDragging ? "scale-[1.02] border-primary bg-primary/5" : "border-border hover:border-primary hover:bg-accent",
        selectedFile && "border-green-500 bg-green-50 dark:bg-green-950",
      )}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) selectFile(file);
          event.target.value = ""; // so choosing the same file again still fires onChange
        }}
      />
      <FileText className="mx-auto mb-4 h-16 w-16 text-muted-foreground" />
      <p className="mb-2 text-lg font-medium">
        {selectedFile ? `Selected: ${selectedFile.name}` : "Drag and drop a PDF file here or click to browse"}
      </p>
      <p className="text-sm text-muted-foreground">
        {selectedFile
          ? `Size: ${(selectedFile.size / 1024 / 1024).toFixed(2)} MB`
          : "Supports research papers in PDF format"}
      </p>
    </button>
  );
}
