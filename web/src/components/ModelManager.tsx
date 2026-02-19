"use client"

import { useState, useEffect } from "react"
import { Download, RefreshCw, Loader2, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useToast } from "@/components/ui/use-toast"

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
}

interface ModelsResponse {
  models: Model[]
  count: number
}

interface AvailableModelsResponse {
  models: AvailableModel[]
  count: number
}

interface DownloadProgress {
  model_name: string
  status: string
  progress: number
  message: string
  total: number
  completed: number
}

export default function ModelManager() {
  const [models, setModels] = useState<Model[]>([])
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([])
  const [filteredModels, setFilteredModels] = useState<AvailableModel[]>([])
  const [loading, setLoading] = useState(true)
  const [installing, setInstalling] = useState<string | null>(null)
  const [downloadProgress, setDownloadProgress] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const { toast } = useToast()

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

  const loadAvailableModels = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/models/available")
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

  const installModel = async (modelName: string) => {
    setInstalling(modelName)
    setDownloadProgress(0)
    setError(null)
    
    try {
      // Start the download
      const response = await fetch("http://localhost:8000/api/models/download", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ model_name: modelName }),
      })

      if (!response.ok) {
        throw new Error("Failed to start model download")
      }

      const data = await response.json()
      const downloadId = data.download_id

      // Show toast notification
      const toastId = toast({
        title: "Downloading Model",
        description: `Installing ${modelName}...`,
      })

      // Connect to WebSocket for progress updates
      const ws = new WebSocket(`ws://localhost:8000/ws/models/download/${downloadId}`)

      ws.onmessage = (event) => {
        const progress: DownloadProgress = JSON.parse(event.data)
        setDownloadProgress(progress.progress)

        // Update toast with progress
        toastId.update({
          id: toastId.id,
          title: "Downloading Model",
          description: `${modelName}: ${progress.progress}% - ${progress.message}`,
        })

        if (progress.status === "completed") {
          ws.close()
          setInstalling(null)
          setDownloadProgress(0)
          loadModels()
          loadAvailableModels()
          
          // Dismiss the progress toast and show success toast
          toastId.dismiss()
          toast({
            title: "Installation Complete",
            description: `${modelName} has been successfully installed!`,
          })
        } else if (progress.status === "error") {
          ws.close()
          setError(progress.message)
          setInstalling(null)
          setDownloadProgress(0)
          
          // Dismiss the progress toast and show error toast
          toastId.dismiss()
          toast({
            title: "Installation Failed",
            description: progress.message,
            variant: "destructive",
          })
        }
      }

      ws.onerror = () => {
        setError("WebSocket connection failed")
        setInstalling(null)
        setDownloadProgress(0)
        toast({
          title: "Connection Error",
          description: "Failed to connect to download progress stream",
          variant: "destructive",
        })
      }

      ws.onclose = () => {
        // Connection closed, check if we need to poll for status
        if (installing === modelName) {
          // Still installing, keep checking
        }
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to install model")
      setInstalling(null)
      setDownloadProgress(0)
      toast({
        title: "Installation Error",
        description: err instanceof Error ? err.message : "Failed to install model",
        variant: "destructive",
      })
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
              disabled={installing !== null}
            />
          </div>

          {/* Progress bar for active download */}
          {installing && (
            <div className="space-y-2 p-3 bg-muted rounded-md">
              <div className="flex items-center justify-between text-sm">
                <span>Installing {installing}...</span>
                <span>{downloadProgress}%</span>
              </div>
              <Progress value={downloadProgress} />
            </div>
          )}

          {/* Available models list */}
          <div className="max-h-96 overflow-y-auto space-y-2 border rounded-md p-2">
            {filteredModels.map((model) => (
              <div
                key={model.name}
                className="flex items-center justify-between p-3 bg-muted/50 rounded-md hover:bg-muted"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium">{model.name}</p>
                  <p className="text-xs text-muted-foreground">{model.description}</p>
                  <p className="text-xs text-muted-foreground mt-1">{model.size}</p>
                </div>
                <Button
                  onClick={() => installModel(model.name)}
                  disabled={installing !== null || model.installed}
                  size="sm"
                  variant={model.installed ? "outline" : "default"}
                >
                  {installing === model.name ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : model.installed ? (
                    "Installed"
                  ) : (
                    <>
                      <Download className="h-4 w-4 mr-1" />
                      Install
                    </>
                  )}
                </Button>
              </div>
            ))}
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
