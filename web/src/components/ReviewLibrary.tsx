"use client"

import { useState, useEffect } from "react"
import { Trash2, Download, Loader2, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { API_URL } from "@/lib/config"

interface StoredReview {
  id: string
  paper_title: string
  pdf_filename: string
  pdf_path: string | null
  reviewer_model: string
  overall_score: number
  recommendation: string
  review_summary: string
  created_at: string
}

interface ReviewsResponse {
  reviews: StoredReview[]
  total: number
  limit: number
  offset: number
}

interface Statistics {
  total_reviews: number
  avg_score: number
  min_score: number
  max_score: number
  unique_papers: number
  unique_models: number
  recommendations: Record<string, number>
}

export default function ReviewLibrary() {
  const [reviews, setReviews] = useState<StoredReview[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [downloading, setDownloading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<Statistics | null>(null)

  const loadReviews = async () => {
    setLoading(true)
    setError(null)
    try {
      const [reviewsResponse, statsResponse] = await Promise.all([
        fetch(`${API_URL}/api/reviews?limit=50`),
        fetch(`${API_URL}/api/statistics`),
      ])

      if (!reviewsResponse.ok || !statsResponse.ok) {
        throw new Error("Failed to fetch reviews")
      }

      const reviewsData: ReviewsResponse = await reviewsResponse.json()
      const statsData = await statsResponse.json()

      setReviews(reviewsData.reviews)
      setStats(statsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reviews")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadReviews()
  }, [])

  const deleteReview = async (reviewId: string) => {
    if (!confirm("Are you sure you want to delete this review?")) {
      return
    }

    setDeleting(reviewId)
    setError(null)
    try {
      const response = await fetch(`${API_URL}/api/reviews/${reviewId}`, {
        method: "DELETE",
      })

      if (!response.ok) {
        throw new Error("Failed to delete review")
      }

      // Reload reviews after deletion
      await loadReviews()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete review")
    } finally {
      setDeleting(null)
    }
  }

  const downloadPDF = async (reviewId: string, filename: string) => {
    setDownloading(reviewId)
    setError(null)
    try {
      const response = await fetch(`${API_URL}/api/reviews/${reviewId}/pdf`)

      if (!response.ok) {
        throw new Error("Failed to download PDF")
      }

      // Create a blob from the response
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download PDF")
    } finally {
      setDownloading(null)
    }
  }

  const getRecommendationColor = (recommendation: string) => {
    const rec = recommendation.toLowerCase()
    if (rec.includes("accept")) return "text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-950"
    if (rec.includes("reject")) return "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950"
    return "text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-950"
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>📚 Review Library</CardTitle>
            <CardDescription>Browse and manage your saved reviews</CardDescription>
          </div>
          <Button onClick={loadReviews} disabled={loading} size="sm" variant="outline">
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

        {/* Statistics */}
        {stats && (
          <div className="grid grid-cols-3 gap-4 p-4 bg-muted rounded-md">
            <div className="text-center">
              <p className="text-2xl font-bold text-primary">{stats.total_reviews}</p>
              <p className="text-xs text-muted-foreground">Total Reviews</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-primary">{stats.avg_score?.toFixed(1)}</p>
              <p className="text-xs text-muted-foreground">Avg Score</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-primary">{stats.unique_papers}</p>
              <p className="text-xs text-muted-foreground">Unique Papers</p>
            </div>
          </div>
        )}

        {/* Reviews list */}
        <div className="space-y-2">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : reviews.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              No reviews yet. Upload a paper to get started!
            </p>
          ) : (
            reviews.map((review) => (
              <div
                key={review.id}
                className="flex items-start justify-between p-4 bg-muted rounded-md hover:bg-muted/80 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-sm truncate">{review.paper_title}</h3>
                  <p className="text-xs text-muted-foreground mb-2">
                    {review.pdf_filename} • {review.reviewer_model} • {formatDate(review.created_at)}
                  </p>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-semibold text-primary">
                      {review.overall_score}/10
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-semibold ${getRecommendationColor(
                        review.recommendation
                      )}`}
                    >
                      {review.recommendation}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {review.review_summary}
                  </p>
                </div>
                <div className="flex gap-1 ml-4">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => downloadPDF(review.id, review.pdf_filename)}
                    disabled={downloading === review.id || !review.pdf_path}
                    title={review.pdf_path ? "Download PDF" : "PDF not available"}
                  >
                    {downloading === review.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Download className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => deleteReview(review.id)}
                    disabled={deleting === review.id}
                  >
                    {deleting === review.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}
