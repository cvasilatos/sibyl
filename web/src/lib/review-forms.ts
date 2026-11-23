/** A review form the user can pick: a bundled conference template or one of their saved custom forms. */
export type FormRef = { kind: "conference" | "custom"; id: string };

/** One string per form, for select values and URLs: "conference:neurips" or "custom:<id>". */
export function formKey(form: FormRef): string {
  return `${form.kind}:${form.id}`;
}

export function parseFormKey(key: string | null | undefined): FormRef | null {
  const match = key?.match(/^(conference|custom):(.+)$/);
  const [, kind, id] = match ?? [];
  return kind && id ? { kind: kind as FormRef["kind"], id } : null;
}

const REVIEW_FORM_EXTENSIONS = [".txt", ".md", ".markdown"];
const REVIEW_FORM_MAX_BYTES = 64 * 1024;

/** Why a custom review form file is rejected, or null when it is acceptable. */
export function reviewFormProblem(file: File): string | null {
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!REVIEW_FORM_EXTENSIONS.includes(extension)) return "Choose a .txt, .md, or .markdown file.";
  if (file.size > REVIEW_FORM_MAX_BYTES) return "The review form must be 64 KiB or smaller.";
  return null;
}

/** A starting name for an uploaded form: its file name without the extension. */
export function suggestedFormName(file: File): string {
  const dot = file.name.lastIndexOf(".");
  return (dot > 0 ? file.name.slice(0, dot) : file.name).replace(/[_-]+/g, " ").trim();
}
