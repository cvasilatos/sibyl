"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useCallback, useRef, useState, useEffect, type RefObject } from "react"

import ModelManager from "@/components/ModelManager"
import ReviewLibrary from "@/components/ReviewLibrary"
import Tabs from "@/components/Tabs"
import UploadArea from "@/components/UploadArea"
import ResultsPanel from "@/components/ResultsPanel"

interface ReviewCriteria {
  novelty: string
  methodology: string
  results: string
  clarity: string
  impact: string
  limitations: string
  strengths: string
  overall_score: number
  recommendation: string
  detailed_feedback: string
}

interface Review {
  paper_title: string
  reviewer_model: string
  criteria: ReviewCriteria
}

interface ComparisonStats {
  mean: number
  std: number
  min: number
  max: number
}

interface ReviewResults {
  paper_title: string
  reviews: Review[]
  comparison: {
    score_statistics: ComparisonStats
    consensus: string
    total_reviews: number
    reviewers: string[]
  }
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<"review" | "library" | "models">("models")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedModel, setSelectedModel] = useState<string>("")
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [isReviewing, setIsReviewing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState("")
  const [results, setResults] = useState<ReviewResults | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null!)
  const wsRef = useRef<WebSocket | null>(null)

  // Load available models on mount
  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/models")
        if (response.ok) {
          const data = await response.json()
          const modelNames = data.models.map((m: any) => m.name)
          setAvailableModels(modelNames)
          if (modelNames.length > 0) {
            setSelectedModel(modelNames[0])
          }
        }
      } catch (err) {
        console.error("Failed to load models:", err)
      }
    }
    loadModels()
  }, [])

  const handleFileSelect = (file: File) => {
    if (file.type === "application/pdf") {
      setSelectedFile(file)
      setError(null)
      setResults(null)
    } else {
      setError("Please select a PDF file")
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
    }
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }, [])

  const startReview = async () => {
    if (!selectedFile) return

    setIsReviewing(true)
    setError(null)
    setResults(null)
    setProgress(0)
    setProgressMessage("Uploading file...")

    try {
      // Upload file
      const formData = new FormData()
      formData.append("file", selectedFile)

      const response = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error("Failed to upload file")
      }

      const data = await response.json()
      const sessionId = data.session_id

      // Connect WebSocket with optional model parameter
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
      const wsUrl = selectedModel 
        ? `${protocol}//localhost:8000/ws/${sessionId}?model=${encodeURIComponent(selectedModel)}`
        : `${protocol}//localhost:8000/ws/${sessionId}`
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data)

        if (message.status === "progress") {
          setProgress(message.progress)
          setProgressMessage(message.message)
        } else if (message.status === "completed") {
          setProgress(100)
          setResults(message.results)
          setIsReviewing(false)
          ws.close()
        } else if (message.status === "error") {
          setError(message.message)
          setIsReviewing(false)
          ws.close()
        }
      }

      ws.onerror = () => {
        setError("Connection error. Please try again.")
        setIsReviewing(false)
      }

      ws.onclose = () => {
        if (isReviewing) {
          setIsReviewing(false)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred")
      setIsReviewing(false)
    }
  }

  const getRecommendationColor = (recommendation: string) => {
    const rec = recommendation.toLowerCase()
    if (rec.includes("accept")) return "text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-950"
    if (rec.includes("reject")) return "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950"
    return "text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-950"
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-500 via-purple-600 to-purple-700 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <Card className="mb-8">
          <CardHeader className="text-center">
            <div className="flex items-center justify-center mb-4">
              <span className="text-6xl">🔮</span>
            </div>
            <CardTitle className="text-4xl font-bold">Sibyl</CardTitle>
            <CardDescription className="text-lg">
              AI-Powered Research Paper Review System
            </CardDescription>
            <p className="text-sm text-muted-foreground mt-2">
              Upload a research paper and get comprehensive AI-powered reviews using local LLM models
            </p>
          </CardHeader>

          {/* Tabs */}
          <div className="border-b px-6">
            <Tabs activeTab={activeTab} setActiveTab={setActiveTab} />
          </div>

          <CardContent className="space-y-6">
            {activeTab === "review" && (
              <UploadArea
                selectedFile={selectedFile}
                selectedModel={selectedModel}
                availableModels={availableModels}
                onModelChange={setSelectedModel}
                fileInputRef={fileInputRef}
                isDragging={isDragging}
                handleDragOver={handleDragOver}
                handleDragLeave={handleDragLeave}
                handleDrop={handleDrop}
                handleFileInputChange={handleFileInputChange}
                startReview={startReview}
                isReviewing={isReviewing}
                progress={progress}
                progressMessage={progressMessage}
                error={error}
              />
            )}

            {activeTab === "library" && <ReviewLibrary />}

            {activeTab === "models" && <ModelManager />}
          </CardContent>
        </Card>

        {/* Results */}
        {results && (
          <ResultsPanel results={results} getRecommendationColor={getRecommendationColor} />
        )}

        {/* Footer */}
        <footer className="text-center text-white mt-8 py-4">
          <p className="text-sm">
            Powered by local LLMs via Ollama • Privacy-first • Zero-cost
          </p>
        </footer>
      </div>
    </div>
  )
}

/* ReviewSection moved to /src/components/ReviewSection.tsx */
