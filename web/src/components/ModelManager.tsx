"use client";

import { Download, Loader2, RefreshCw, Search, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useDownload } from "@/hooks/use-download";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/presentation";
import type { AvailableModel, EngineInfo, InstalledModel } from "@/lib/types";

export default function ModelManager() {
  const [models, setModels] = useState<InstalledModel[]>([]);
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [removing, setRemoving] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [modelTags, setModelTags] = useState<Record<string, string[]>>({});
  const [fetchingTags, setFetchingTags] = useState<Set<string>>(new Set());
  const [selectedTags, setSelectedTags] = useState<Record<string, string>>({});
  const [expandedModel, setExpandedModel] = useState<string | null>(null);
  const [engine, setEngine] = useState<EngineInfo | null>(null);
  const { toast } = useToast();
  const { installing, error, startDownload, clearError } = useDownload();

  const loadModels = useCallback(async () => {
    setLoading(true);
    clearError();
    try {
      const data = await api.listInstalledModels();
      setModels(data.models || []);
    } catch (err) {
      // Note: error handling moved to context
      console.error("Failed to load models:", err);
    } finally {
      setLoading(false);
    }
  }, [clearError]);

  const loadAvailableModels = useCallback(async () => {
    try {
      const data = await api.listAvailableModels();
      setAvailableModels(data.models || []);
    } catch (err) {
      console.error("Failed to load available models:", err);
    }
  }, []);

  useEffect(() => {
    loadModels();
    loadAvailableModels();
    api
      .getEngine()
      .then(setEngine)
      .catch((err) => console.error("Failed to load engine info:", err));
  }, [loadAvailableModels, loadModels]);

  const filteredModels = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return availableModels;
    return availableModels.filter((model) => model.name.toLowerCase().includes(query) || model.description.toLowerCase().includes(query));
  }, [availableModels, searchQuery]);

  const fetchModelTags = async (modelName: string) => {
    if (modelTags[modelName] !== undefined || fetchingTags.has(modelName)) return;
    setFetchingTags((prev) => new Set(prev).add(modelName));
    try {
      const data = await api.listModelTags(modelName);
      setModelTags((prev) => ({ ...prev, [modelName]: data.tags }));
      if (data.tags.length > 0) {
        setSelectedTags((prev) => ({ ...prev, [modelName]: data.tags[0] }));
      }
    } catch (err) {
      console.error(`Failed to load tags for ${modelName}:`, err);
      setModelTags((prev) => ({ ...prev, [modelName]: [] }));
    } finally {
      setFetchingTags((prev) => {
        const next = new Set(prev);
        next.delete(modelName);
        return next;
      });
    }
  };

  const removeModel = async (modelName: string) => {
    if (!window.confirm(`Delete ${modelName}? It will need to be downloaded again to use it.`)) return;
    setRemoving((prev) => new Set(prev).add(modelName));
    try {
      await api.deleteModel(modelName);
      toast({ title: "Model Removed", description: `${modelName} was deleted.` });
      await Promise.all([loadModels(), loadAvailableModels()]);
    } catch (err) {
      toast({ title: "Removal Failed", description: err instanceof Error ? err.message : "Could not delete model", variant: "destructive" });
    } finally {
      setRemoving((prev) => {
        const next = new Set(prev);
        next.delete(modelName);
        return next;
      });
    }
  };

  const handleInstallClick = async (modelName: string) => {
    if (expandedModel === modelName) {
      setExpandedModel(null);
      return;
    }
    setExpandedModel(modelName);
    await fetchModelTags(modelName);
  };

  const doInstall = (fullModelName: string) => {
    clearError();
    setExpandedModel(null);

    const toastId = toast({
      title: "Downloading Model",
      description: `Installing ${fullModelName}...`,
    });

    startDownload(
      fullModelName,
      () => {
        loadModels();
        loadAvailableModels();
        toastId.dismiss();
        toast({
          title: "Installation Complete",
          description: `${fullModelName} has been successfully installed!`,
        });
      },
      (message: string) => {
        toastId.dismiss();
        toast({
          title: "Installation Failed",
          description: message,
          variant: "destructive",
        });
      },
      (progress: number, message: string) => {
        toastId.update({
          id: toastId.id,
          title: "Downloading Model",
          description: `${fullModelName}: ${progress}% - ${message}`,
        });
      }
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>🤖 {engine?.label ?? "Local"} Models</CardTitle>
            <CardDescription>
              {engine?.name === "vllm"
                ? "Download models from Hugging Face; Sibyl starts vLLM on the selected GPU when a review needs it"
                : engine && !engine.supports_downloads
                  ? "Models are managed by your inference server; Sibyl lists what it serves"
                  : "Manage your local models"}
            </CardDescription>
          </div>
          <Button onClick={loadModels} disabled={loading} size="sm" variant="outline">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="p-3 bg-destructive/10 border border-destructive rounded-md">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Search and install models */}
        <div className={`space-y-2 ${engine && !engine.supports_downloads ? "hidden" : ""}`}>
          <h3 className="text-sm font-semibold">Browse & Install Models</h3>

          {/* Search box */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search models by name or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-3 py-2 text-sm border border-input rounded-md bg-background"
            />
          </div>

          {/* Progress bar for active download */}
          {/* Moved to global layout */}

          {/* Available models list */}
          <div className="max-h-96 overflow-y-auto space-y-2 border rounded-md p-2">
            {filteredModels.map((model) => {
              const tags = modelTags[model.name];
              const isFetchingTags = fetchingTags.has(model.name);
              const isExpanded = expandedModel === model.name;
              const selectedTag = selectedTags[model.name];
              const isInstallingModel = installing.some((n) => n === model.name || n.startsWith(`${model.name}:`));
              const hasInstalledVariants = model.installed_variants && model.installed_variants.length > 0;
              const isSelectedVariantInstalled = hasInstalledVariants && !!selectedTag && model.installed_variants?.includes(selectedTag);
              return (
                <div key={model.name} className="p-3 bg-muted/50 rounded-md hover:bg-muted">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium">{model.name}</p>
                      <p className="text-xs text-muted-foreground">{model.description}</p>
                      <p className="text-xs text-muted-foreground mt-1">{model.size}</p>
                      {hasInstalledVariants && <p className="text-xs text-green-600 mt-1">Installed: {model.installed_variants?.join(", ")}</p>}
                      {model.installed && !hasInstalledVariants && <p className="text-xs text-green-600 mt-1">Installed</p>}
                    </div>
                    <Button onClick={() => handleInstallClick(model.name)} disabled={isInstallingModel} size="sm" variant="default">
                      {isInstallingModel ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <>
                          <Download className="h-4 w-4 mr-1" />
                          {hasInstalledVariants ? "More Variants" : "Install"}
                        </>
                      )}
                    </Button>
                  </div>
                  {isExpanded && (
                    <div className="mt-2 pt-2 border-t border-border">
                      {isFetchingTags ? (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Loading variants…
                        </div>
                      ) : tags && tags.length > 0 ? (
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs text-muted-foreground">Variant:</span>
                          <select
                            value={selectedTag}
                            onChange={(e) => setSelectedTags((prev) => ({ ...prev, [model.name]: e.target.value }))}
                            className="text-xs border border-input rounded px-2 py-1 bg-background"
                          >
                            {tags.map((tag) => (
                              <option key={tag} value={tag}>
                                {tag}
                                {model.installed_variants?.includes(tag) ? " (installed)" : ""}
                              </option>
                            ))}
                          </select>
                          <Button size="sm" onClick={() => doInstall(`${model.name}:${selectedTag}`)} disabled={isInstallingModel || isSelectedVariantInstalled}>
                            <Download className="h-3 w-3 mr-1" />
                            Confirm
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">{engine?.name === "vllm" ? model.name : "No size variants found."}</span>
                          <Button size="sm" onClick={() => doInstall(model.name)} disabled={isInstallingModel || model.installed}>
                            <Download className="h-3 w-3 mr-1" />
                            {engine?.name === "vllm" ? "Download" : "Install latest"}
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
            {filteredModels.length === 0 && <p className="text-sm text-muted-foreground text-center py-4">No models found matching "{searchQuery}"</p>}
          </div>
        </div>

        {/* Installed models */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold">Installed Models ({models.length})</h3>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : models.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">No models installed. Install one from above.</p>
          ) : (
            <div className="space-y-2">
              {models.map((model) => (
                <div key={model.digest} className="flex items-center justify-between p-3 bg-muted rounded-md">
                  <div>
                    <p className="text-sm font-medium">{model.model}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatBytes(model.size)} • Modified {formatDate(model.modified_at)}
                    </p>
                  </div>
                  <Button onClick={() => removeModel(model.model)} disabled={removing.has(model.model)} size="sm" variant="destructive">
                    {removing.has(model.model) ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
