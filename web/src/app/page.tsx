"use client"

import { useState, useCallback, useRef } from "react"
import { Upload, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"

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
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isReviewing, setIsReviewing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState("")
  const [results, setResults] = useState<ReviewResults | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

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

      // Connect WebSocket
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
      const ws = new WebSocket(`${protocol}//localhost:8000/ws/${sessionId}`)
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
    <div className="min-h-screen bg-gradient-to-br from-violet-900 via-purple-900 to-indigo-900 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <Card className="mb-8">
          <CardHeader className="text-center border-b pb-6">
            <div className="flex items-center justify-center mb-2">
              <span className="text-6xl">🔮</span>
            </div>
            <CardTitle className="text-4xl font-bold mb-2">Sibyl</CardTitle>
            <CardDescription className="text-lg font-medium">
              AI-Powered Research Paper Review System
            </CardDescription>
            <div className="mt-4 space-y-1">
              <p className="text-sm font-semibold text-primary">
                NYU Center for Cybersecurity
              </p>
              <p className="text-sm font-semibold text-primary">
                MoMA Group - Mobile Security and Communications Systems
              </p>
            </div>
            <p className="text-sm text-muted-foreground mt-3">
              Upload a research paper and get comprehensive AI-powered reviews using local LLM models
            </p>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* Upload Area */}
            <div
              className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-all ${
                isDragging
                  ? "border-primary bg-primary/5 scale-[1.02]"
                  : "border-border hover:border-primary hover:bg-accent"
              } ${selectedFile ? "border-green-500 bg-green-50 dark:bg-green-950" : ""}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileInputChange}
                className="hidden"
              />
              <FileText className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
              <p className="text-lg font-medium mb-2">
                {selectedFile
                  ? `Selected: ${selectedFile.name}`
                  : "Drag and drop a PDF file here or click to browse"}
              </p>
              <p className="text-sm text-muted-foreground">
                {selectedFile
                  ? `Size: ${(selectedFile.size / 1024 / 1024).toFixed(2)} MB`
                  : "Supports research papers in PDF format"}
              </p>
            </div>

            {/* Start Review Button */}
            <Button
              onClick={startReview}
              disabled={!selectedFile || isReviewing}
              className="w-full"
              size="lg"
            >
              <Upload className="mr-2 h-4 w-4" />
              {isReviewing ? "Reviewing..." : "Start Review"}
            </Button>

            {/* Progress */}
            {isReviewing && (
              <div className="space-y-2">
                <Progress value={progress} className="h-2" />
                <p className="text-sm text-center text-muted-foreground">
                  {progressMessage} ({progress}%)
                </p>
              </div>
            )}

            {/* Error */}
            {error && (
              <Card className="border-destructive">
                <CardContent className="p-4">
                  <p className="text-destructive">❌ Error: {error}</p>
                </CardContent>
              </Card>
            )}
          </CardContent>
        </Card>

        {/* Results */}
        {results && (
          <div className="space-y-6">
            {/* Statistics Card */}
            <Card>
              <CardHeader>
                <CardTitle>📊 Overall Statistics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="font-medium">Mean Score:</span>
                  <span className="text-primary font-semibold">
                    {results.comparison.score_statistics.mean.toFixed(2)}/10
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">Standard Deviation:</span>
                  <span>{results.comparison.score_statistics.std.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">Score Range:</span>
                  <span>
                    {results.comparison.score_statistics.min} -{" "}
                    {results.comparison.score_statistics.max}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">Consensus:</span>
                  <span className="font-semibold">{results.comparison.consensus}</span>
                </div>
              </CardContent>
            </Card>

            {/* Individual Reviews */}
            {results.reviews.map((review, index) => (
              <Card key={index}>
                <CardHeader>
                  <div className="flex items-center justify-between flex-wrap gap-4">
                    <CardTitle className="flex items-center gap-2">
                      🤖 {review.reviewer_model}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <span className="text-3xl font-bold text-primary">
                        {review.criteria.overall_score}/10
                      </span>
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-semibold ${getRecommendationColor(
                          review.criteria.recommendation
                        )}`}
                      >
                        {review.criteria.recommendation}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ReviewSection title="💡 Novelty" content={review.criteria.novelty} />
                  <ReviewSection title="🔬 Methodology" content={review.criteria.methodology} />
                  <ReviewSection title="📈 Results" content={review.criteria.results} />
                  <ReviewSection title="✍️ Clarity" content={review.criteria.clarity} />
                  <ReviewSection title="🎯 Impact" content={review.criteria.impact} />
                  <ReviewSection title="💪 Strengths" content={review.criteria.strengths} />
                  <ReviewSection title="⚠️ Limitations" content={review.criteria.limitations} />
                  <ReviewSection
                    title="📝 Detailed Feedback"
                    content={review.criteria.detailed_feedback}
                  />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Footer */}
        <footer className="text-center text-white mt-8 py-6 space-y-3 bg-white/10 rounded-lg backdrop-blur-sm">
          <div className="space-y-1">
            <p className="text-base font-semibold">
              NYU Center for Cybersecurity
            </p>
            <p className="text-sm font-medium">
              MoMA Group - Mobile Security and Communications Systems
            </p>
          </div>
          <p className="text-sm opacity-90">
            Powered by local LLMs via Ollama • Privacy-first • Zero-cost
          </p>
          <p className="text-xs opacity-75">
            New York University Tandon School of Engineering
          </p>
        </footer>
      </div>
    </div>
  )
}

function ReviewSection({ title, content }: { title: string; content: string }) {
  return (
    <div className="space-y-1">
      <h4 className="font-semibold text-sm">{title}</h4>
      <p className="text-sm text-muted-foreground bg-muted p-3 rounded-md">{content}</p>
    </div>
  )
}
