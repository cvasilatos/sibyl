"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LoadingBlock, Spinner } from "@/components/ui/spinner";
import { toast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { invalidates, queries } from "@/lib/api/queries";
import { formatBytes, formatDate } from "@/lib/format";

export default function InstalledModels() {
  const queryClient = useQueryClient();
  const { data: models = [], isPending } = useQuery(queries.installedModels());
  const remove = useMutation({
    mutationFn: api.deleteModel,
    onSuccess: (_, modelName) => {
      toast({ title: "Model Removed", description: `${modelName} was deleted.` });
      return queryClient.invalidateQueries(invalidates.models);
    },
    onError: (err) => toast({ title: "Removal Failed", description: err.message || "Could not delete model", variant: "destructive" }),
  });

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">Installed Models ({models.length})</h3>
      {isPending ? (
        <LoadingBlock />
      ) : models.length === 0 ? (
        <p className="py-4 text-center text-sm text-muted-foreground">No models installed. Install one from above.</p>
      ) : (
        <div className="space-y-2">
          {models.map((model) => {
            const removing = remove.isPending && remove.variables === model.model;
            return (
              <div key={model.digest} className="flex items-center justify-between rounded-md bg-muted p-3">
                <div>
                  <p className="text-sm font-medium">{model.model}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatBytes(model.size)} • Modified {formatDate(model.modified_at)}
                  </p>
                </div>
                <Button
                  onClick={() => window.confirm(`Delete ${model.model}? It will need to be downloaded again to use it.`) && remove.mutate(model.model)}
                  disabled={removing}
                  size="sm"
                  variant="destructive"
                  aria-label={`Delete ${model.model}`}
                >
                  {removing ? <Spinner label="Removing" /> : <Trash2 className="h-4 w-4" />}
                </Button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
