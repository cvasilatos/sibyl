"use client";

import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import { Spinner } from "@/components/ui/spinner";
import { queries } from "@/lib/api/queries";
import type { AvailableModel } from "@/lib/types";
import { useDownload } from "./download-context";

type Props = {
  model: AvailableModel;
  expanded: boolean;
  onToggle: () => void;
  /** True for vLLM, where a model is a Hugging Face repo without size tags. */
  isVllm: boolean;
};

/** A downloadable model; expanded, it offers its size variants (tags). */
export default function ModelCatalogItem({ model, expanded, onToggle, isVllm }: Props) {
  const { installing, startDownload } = useDownload();
  const tags = useQuery({ ...queries.modelTags(model.name), enabled: expanded });
  const [chosenTag, setChosenTag] = useState<string | null>(null);
  const selectedTag = chosenTag ?? tags.data?.[0];

  const installed = model.installed_variants ?? [];
  const isInstalling = installing.some((n) => n === model.name || n.startsWith(`${model.name}:`));
  const install = (fullName: string) => {
    onToggle();
    startDownload(fullName);
  };

  return (
    <div className="rounded-md bg-muted/50 p-3 hover:bg-muted">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium">{model.name}</p>
          <p className="text-xs text-muted-foreground">{model.description}</p>
          <p className="mt-1 text-xs text-muted-foreground">{model.size}</p>
          {installed.length > 0 && <p className="mt-1 text-xs text-green-600">Installed: {installed.join(", ")}</p>}
          {model.installed && installed.length === 0 && <p className="mt-1 text-xs text-green-600">Installed</p>}
        </div>
        <Button onClick={onToggle} disabled={isInstalling} size="sm" variant="default" aria-expanded={expanded}>
          {isInstalling ? (
            <Spinner label="Installing" />
          ) : (
            <>
              <Download className="mr-1 h-4 w-4" />
              {installed.length > 0 ? "More Variants" : "Install"}
            </>
          )}
        </Button>
      </div>
      {expanded && (
        <div className="mt-2 border-t border-border pt-2">
          {tags.isPending ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Spinner className="h-3 w-3" />
              Loading variants…
            </div>
          ) : tags.data && tags.data.length > 0 && selectedTag ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground">Variant:</span>
              <NativeSelect aria-label={`Variant of ${model.name}`} value={selectedTag} onChange={(e) => setChosenTag(e.target.value)} className="w-auto px-2 py-1 text-xs">
                {tags.data.map((tag) => (
                  <option key={tag} value={tag}>
                    {tag}
                    {installed.includes(tag) ? " (installed)" : ""}
                  </option>
                ))}
              </NativeSelect>
              <Button size="sm" onClick={() => install(`${model.name}:${selectedTag}`)} disabled={isInstalling || installed.includes(selectedTag)}>
                <Download className="mr-1 h-3 w-3" />
                Confirm
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">{isVllm ? model.name : "No size variants found."}</span>
              <Button size="sm" onClick={() => install(model.name)} disabled={isInstalling || model.installed}>
                <Download className="mr-1 h-3 w-3" />
                {isVllm ? "Download" : "Install latest"}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
