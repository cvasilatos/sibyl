"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import SearchInput from "@/components/SearchInput";
import { queries } from "@/lib/api/queries";
import ModelCatalogItem from "./ModelCatalogItem";

/** Searchable list of models the engine can download. */
export default function ModelCatalog({ isVllm }: { isVllm: boolean }) {
  const { data: models = [] } = useQuery(queries.availableModels());
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedModel, setExpandedModel] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return models;
    return models.filter((model) => model.name.toLowerCase().includes(query) || model.description.toLowerCase().includes(query));
  }, [models, searchQuery]);

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">Browse & Install Models</h3>
      <SearchInput value={searchQuery} onChange={setSearchQuery} placeholder="Search models by name or description…" />
      <div className="max-h-96 space-y-2 overflow-y-auto rounded-md border p-2">
        {filtered.map((model) => (
          <ModelCatalogItem
            key={model.name}
            model={model}
            isVllm={isVllm}
            expanded={expandedModel === model.name}
            onToggle={() => setExpandedModel((current) => (current === model.name ? null : model.name))}
          />
        ))}
        {filtered.length === 0 && <p className="py-4 text-center text-sm text-muted-foreground">No models found matching "{searchQuery}"</p>}
      </div>
    </div>
  );
}
