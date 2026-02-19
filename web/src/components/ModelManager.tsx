"use client"

import { useState, useEffect } from "react"
import { Download, RefreshCw, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface Model {
  name: string
  size: number
  modified_at: string
  digest: string
}

interface ModelsResponse {
  models: Model[]
  count: number
}

export default function ModelManager() {
  const [models, setModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(true)
  const [installing, setInstalling] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [newModelName, setNewModelName] = useState("")

  const loadModels = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch("http://localhost:8000/api/models")
      if (!response.ok) {
        throw new Error("Failed to fetch models")
      }
      const data: ModelsResponse = await response.json()
      setModels(data.models || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load models")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadModels()
  }, [])

  const installModel = async (modelName: string) => {
    setInstalling(modelName)
    setError(null)
    try {
      const response = await fetch("http://localhost:8000/api/models/download", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ model_name: modelName }),
      })

      if (!response.ok) {
        throw new Error("Failed to install model")
      }

      // Reload models after installation
      await loadModels()
      setNewModelName("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to install model")
    } finally {
      setInstalling(null)
    }
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

  const popularModels = [
    "llama3.2",
    "llama3.1",
    "mistral",
    "phi3",
    "qwen2.5",
    "gemma2",
  ]

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

        {/* Install new model */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold">Install Model</h3>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Enter model name (e.g., llama3.2)"
              value={newModelName}
              onChange={(e) => setNewModelName(e.target.value)}
              className="flex-1 px-3 py-2 text-sm border border-input rounded-md bg-background"
              disabled={installing !== null}
            />
            <Button
              onClick={() => installModel(newModelName)}
              disabled={!newModelName || installing !== null}
              size="sm"
            >
              {installing === newModelName ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
            </Button>
          </div>

          {/* Popular models */}
          <div className="flex flex-wrap gap-2">
            {popularModels.map((model) => (
              <button
                key={model}
                onClick={() => installModel(model)}
                disabled={installing !== null}
                className="px-2 py-1 text-xs bg-muted hover:bg-muted/80 rounded-md disabled:opacity-50"
              >
                {installing === model ? (
                  <span className="flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Installing...
                  </span>
                ) : (
                  model
                )}
              </button>
            ))}
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
