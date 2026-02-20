"use client"

import { useState, useEffect } from "react"
import { Download, RefreshCw, Loader2, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/components/ui/use-toast"
import { API_URL } from "@/lib/config"
import { useDownload } from "@/lib/download-context"

interface Model {
  name: string
  size: number
  modified_at: string
  digest: string
}

interface AvailableModel {
  name: string
  description: string
  size: string
  installed: boolean
  installed_variants?: string[]
}

interface ModelsResponse {
  models: Model[]
  count: number
}

interface AvailableModelsResponse {
  models: AvailableModel[]
  count: number
}

interface ModelTagsResponse {
  model: string
  tags: string[]
}

export default function ModelManager() {
  const [models, setModels] = useState<Model[]>([])
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([])
  const [filteredModels, setFilteredModels] = useState<AvailableModel[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [modelTags, setModelTags] = useState<Record<string, string[]>>({})
  const [fetchingTags, setFetchingTags] = useState<Set<string>>(new Set())
  const [selectedTags, setSelectedTags] = useState<Record<string, string>>({})
  const [expandedModel, setExpandedModel] = useState<string | null>(null)
  const { toast } = useToast()
  const { installing, error, startDownload, clearError } = useDownload()

  const loadModels = async () => {
    setLoading(true)
    clearError()
    try {
      const response = await fetch(`${API_URL}/api/models`)
      if (!response.ok) {
        throw new Error("Failed to fetch models")
      }
      const data: ModelsResponse = await response.json()
      setModels(data.models || [])
    } catch (err) {
      // Note: error handling moved to context
      console.error("Failed to load models:", err)
    } finally {
      setLoading(false)
    }
  }

  const loadAvailableModels = async () => {
    try {
      const response = await fetch(`${API_URL}/api/models/available`)
      if (!response.ok) {
        throw new Error("Failed to fetch available models")
      }
      const data: AvailableModelsResponse = await response.json()
      setAvailableModels(data.models || [])
      setFilteredModels(data.models || [])
    } catch (err) {
      console.error("Failed to load available models:", err)
    }
  }

  useEffect(() => {
    loadModels()
    loadAvailableModels()
  }, [])

  useEffect(() => {
    // Filter available models based on search query
    if (searchQuery.trim() === "") {
      setFilteredModels(availableModels)
    } else {
      const query = searchQuery.toLowerCase()
      const filtered = availableModels.filter(
        (model) =>
          model.name.toLowerCase().includes(query) ||
          model.description.toLowerCase().includes(query)
      )
      setFilteredModels(filtered)
    }
  }, [searchQuery, availableModels])

  const fetchModelTags = async (modelName: string) => {
    if (modelTags[modelName] !== undefined || fetchingTags.has(modelName)) return
    setFetchingTags((prev) => new Set(prev).add(modelName))
    try {
      const response = await fetch(`${API_URL}/api/models/available/${modelName}/tags`)
      if (!response.ok) throw new Error("Failed to fetch tags")
      const data: ModelTagsResponse = await response.json()
      setModelTags((prev) => ({ ...prev, [modelName]: data.tags }))
      if (data.tags.length > 0) {
        setSelectedTags((prev) => ({ ...prev, [modelName]: data.tags[0] }))
      }
    } catch (err) {
      console.error(`Failed to load tags for ${modelName}:`, err)
      setModelTags((prev) => ({ ...prev, [modelName]: [] }))
    } finally {
      setFetchingTags((prev) => { const next = new Set(prev); next.delete(modelName); return next })
    }
  }

  const handleInstallClick = async (modelName: string) => {
    if (expandedModel === modelName) {
      setExpandedModel(null)
      return
    }
    setExpandedModel(modelName)
    await fetchModelTags(modelName)
  }

  const doInstall = (fullModelName: string) => {
    clearError()
    setExpandedModel(null)

    const toastId = toast({
      title: "Downloading Model",
      description: `Installing ${fullModelName}...`,
    })

    startDownload(
      fullModelName,
      () => {
        loadModels()
        loadAvailableModels()
        toastId.dismiss()
        toast({
          title: "Installation Complete",
          description: `${fullModelName} has been successfully installed!`,
        })
      },
      (message: string) => {
        toastId.dismiss()
        toast({
          title: "Installation Failed",
          description: message,
          variant: "destructive",
        })
      },
      (progress: number, message: string) => {
        toastId.update({
          id: toastId.id,
          title: "Downloading Model",
          description: `${fullModelName}: ${progress}% - ${message}`,
        })
      }
    )
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B"
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB"
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + " MB"
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB"
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>🤖 Ollama Models</CardTitle>
            <CardDescription>Manage your local Ollama models</CardDescription>
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
        <div className="space-y-2">
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
              const tags = modelTags[model.name]
              const isFetchingTags = fetchingTags.has(model.name)
              const isExpanded = expandedModel === model.name
              const selectedTag = selectedTags[model.name]
              const isInstallingModel = installing.some(
                (n) => n === model.name || n.startsWith(`${model.name}:`)
              )
              const hasInstalledVariants = model.installed_variants && model.installed_variants.length > 0
              const isSelectedVariantInstalled = hasInstalledVariants && !!selectedTag && model.installed_variants!.includes(selectedTag)
              return (
                <div
                  key={model.name}
                  className="p-3 bg-muted/50 rounded-md hover:bg-muted"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium">{model.name}</p>
                      <p className="text-xs text-muted-foreground">{model.description}</p>
                      <p className="text-xs text-muted-foreground mt-1">{model.size}</p>
                      {hasInstalledVariants && (
                        <p className="text-xs text-green-600 mt-1">
                          Installed: {model.installed_variants!.join(", ")}
                        </p>
                      )}
                    </div>
                    <Button
                      onClick={() => handleInstallClick(model.name)}
                      disabled={isInstallingModel}
                      size="sm"
                      variant="default"
                    >
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
                                {tag}{model.installed_variants?.includes(tag) ? " (installed)" : ""}
                              </option>
                            ))}
                          </select>
                          <Button
                            size="sm"
                            onClick={() => doInstall(`${model.name}:${selectedTag}`)}
                            disabled={isInstallingModel || isSelectedVariantInstalled}
                          >
                            <Download className="h-3 w-3 mr-1" />
                            Confirm
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">No size variants found.</span>
                          <Button size="sm" onClick={() => doInstall(model.name)} disabled={isInstallingModel}>
                            <Download className="h-3 w-3 mr-1" />
                            Install latest
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
            {filteredModels.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">
                No models found matching "{searchQuery}"
              </p>
            )}
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
            <p className="text-sm text-muted-foreground py-4 text-center">
              No models installed. Install one from above.
            </p>
          ) : (
            <div className="space-y-2">
              {models.map((model) => (
                <div
                  key={model.digest}
                  className="flex items-center justify-between p-3 bg-muted rounded-md"
                >
                  <div>
                    <p className="text-sm font-medium">{model.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatSize(model.size)} • Modified {formatDate(model.modified_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
