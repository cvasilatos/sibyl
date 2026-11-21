"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { ErrorAlert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { invalidates, queries } from "@/lib/api/queries";
import type { EngineInfo } from "@/lib/types";
import { useDownload } from "./download-context";
import InstalledModels from "./InstalledModels";
import ModelCatalog from "./ModelCatalog";

function engineDescription(engine: EngineInfo | undefined): string {
  if (engine?.name === "vllm") return "Download models from Hugging Face; Sibyl starts vLLM on the selected GPU when a review needs it";
  if (engine && !engine.supports_downloads) return "Models are managed by your inference server; Sibyl lists what it serves";
  return "Manage your local models";
}

export default function ModelManager() {
  const queryClient = useQueryClient();
  const { data: engine } = useQuery(queries.engine());
  const { isFetching } = useQuery(queries.installedModels());
  const { error, clearError } = useDownload();

  const refresh = () => {
    clearError();
    queryClient.invalidateQueries(invalidates.models);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>🤖 {engine?.label ?? "Local"} Models</CardTitle>
            <CardDescription>{engineDescription(engine)}</CardDescription>
          </div>
          <Button onClick={refresh} disabled={isFetching} size="sm" variant="outline" aria-label="Refresh models">
            <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ErrorAlert>{error}</ErrorAlert>
        {(!engine || engine.supports_downloads) && <ModelCatalog isVllm={engine?.name === "vllm"} />}
        <InstalledModels />
      </CardContent>
    </Card>
  );
}
