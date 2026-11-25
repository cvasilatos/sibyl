"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import AddReviewFormButton from "@/components/AddReviewFormButton";
import { Button } from "@/components/ui/button";
import { useCanManage } from "@/hooks/use-current-user";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { invalidates, queries } from "@/lib/api/queries";
import { groupByArea } from "@/lib/conferences";
import { conferenceOptionLabel } from "@/lib/page-limit";
import { formKey, parseFormKey } from "@/lib/review-forms";
import { cn } from "@/lib/utils";
import FormViewer from "./FormViewer";

type Props = {
  /** Key of the form shown ("conference:<id>" or "custom:<id>"), or null. */
  selectedKey: string | null;
  onSelect: (key: string | null) => void;
  /** Start a review with this form; the button is hidden when not given. */
  onUse?: (key: string) => void;
};

function Group({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2 px-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>
        {action}
      </div>
      <ul className="space-y-0.5">{children}</ul>
    </div>
  );
}

function Item({
  label,
  active,
  onClick,
  children,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  children?: ReactNode;
}) {
  return (
    <li className={cn("group flex items-center rounded-md", active ? "bg-primary/10 text-primary" : "hover:bg-muted")}>
      <button
        type="button"
        aria-current={active ? "true" : undefined}
        onClick={onClick}
        className="min-w-0 flex-1 truncate px-2 py-1.5 text-left text-sm"
        title={label}
      >
        {label}
      </button>
      {children}
    </li>
  );
}

/** Every reviewer form available: the user's saved forms and the bundled conference forms, with the chosen one's text. */
export default function ReviewFormsBrowser({ selectedKey, onSelect, onUse }: Props) {
  const queryClient = useQueryClient();
  const mayDelete = useCanManage();
  const { data: conferences = [] } = useQuery(queries.conferences());
  const { data: savedForms = [], isSuccess: savedLoaded } = useQuery(queries.reviewForms());
  const selected = parseFormKey(selectedKey);
  const conference = selected?.kind === "conference" ? conferences.find((c) => c.id === selected.id) : undefined;
  const savedForm = selected?.kind === "custom" ? savedForms.find((f) => f.id === selected.id) : undefined;
  // A saved form is shown only while it exists; a conference link works before the list loads.
  const shown = selected?.kind === "custom" ? (savedLoaded && savedForm ? selected : null) : selected;

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteReviewForm(id),
    onSuccess: (_, id) => {
      if (selected?.kind === "custom" && selected.id === id) onSelect(null);
      return queryClient.invalidateQueries(invalidates.reviewForms);
    },
    onError: (error) => toast({ title: "Delete Failed", description: error.message, variant: "destructive" }),
  });

  return (
    <div className="grid grid-cols-1 items-start gap-4 md:grid-cols-[minmax(14rem,1fr)_3fr]">
      <nav
        aria-label="Review forms"
        className="space-y-4 rounded-lg border bg-card p-2 md:sticky md:top-4 md:max-h-[85vh] md:overflow-y-auto"
      >
        <Group title="Saved forms">
          {savedForms.map((form) => {
            const key = formKey({ kind: "custom", id: form.id });
            return (
              <Item key={form.id} label={form.name} active={key === selectedKey} onClick={() => onSelect(key)}>
                {mayDelete(form.owner) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 shrink-0 p-0 text-muted-foreground opacity-60 hover:text-destructive group-hover:opacity-100"
                    aria-label={`Delete ${form.name}`}
                    disabled={remove.isPending}
                    onClick={() => window.confirm(`Delete the review form "${form.name}"?`) && remove.mutate(form.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </Item>
            );
          })}
          {savedLoaded && savedForms.length === 0 && (
            <li className="px-2 py-1 text-xs text-muted-foreground">No saved forms yet.</li>
          )}
          <li className="px-1 pt-1">
            <AddReviewFormButton
              className="w-full"
              label="Add Review Form"
              onSaved={(form) => onSelect(formKey({ kind: "custom", id: form.id }))}
            />
          </li>
        </Group>
        {groupByArea(conferences).map(([area, items]) => (
          <Group key={area} title={area}>
            {items.map((c) => {
              const key = formKey({ kind: "conference", id: c.id });
              return (
                <Item
                  key={c.id}
                  label={conferenceOptionLabel(c)}
                  active={key === selectedKey}
                  onClick={() => onSelect(key)}
                />
              );
            })}
          </Group>
        ))}
      </nav>

      {shown ? (
        <FormViewer
          key={selectedKey}
          form={shown}
          conference={conference}
          savedForm={savedForm}
          onUse={onUse && selectedKey ? () => onUse(selectedKey) : undefined}
        />
      ) : (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-12 text-center text-sm text-muted-foreground">
          <FileText className="h-8 w-8" />
          <p>Choose a form to read it, or add your own.</p>
          <p className="text-xs">
            Conference forms are answered question by question with their official score scales; your forms are
            completed section by section.
          </p>
        </div>
      )}
    </div>
  );
}
