"use client"

import { useState, useEffect } from "react"
import { Trash2, Download, Loader2, RefreshCw, ChevronDown, ChevronUp, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { API_URL, fetchMaxScore } from "@/lib/config"
import ReviewSection from "@/components/ReviewSection"
import { toast } from "@/components/ui/use-toast"

interface StoredReview {
  id: string
  paper_title: string
  pdf_filename: string
  pdf_path: string | null
  reviewer_model: string
  score: number
  recommendation: string
  review_summary: string
  created_at: string
}

interface ReviewCriteria {
  novelty: string
  methodology: string
  results: string
  clarity: string
  impact: string
  limitations: string
  strengths: string
  score: number
  recommendation: string
  detailed_feedback: string
}

interface FullReview {
  id: string
  paper_title: string
  pdf_filename: string
  pdf_path: string | null
  reviewer_model: string
  score: number
  recommendation: string
  created_at: string
  criteria: ReviewCriteria
  raw_response: string
}

interface ReviewsResponse {
  reviews: StoredReview[]
  total: number
  limit: number
  offset: number
}

interface Statistics {
  total_reviews: number
  unique_papers: number
  unique_models: number
  recommendations: Record<string, number>
}

export default function ReviewLibrary({
  initialExpandedReview = null,
  onReviewExpand,
}: {
  initialExpandedReview?: string | null
  onReviewExpand?: (reviewId: string | null) => void
}) {
  const [reviews, setReviews] = useState<StoredReview[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [deletingAll, setDeletingAll] = useState(false)
  const [downloading, setDownloading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<Statistics | null>(null)
  const [expandedReview, setExpandedReview] = useState<string | null>(initialExpandedReview)
  const [fullReviewData, setFullReviewData] = useState<Record<string, FullReview>>({})
  const [loadingFull, setLoadingFull] = useState<string | null>(null)
  const [maxScore, setMaxScore] = useState<number>(10)
  const [selectedPaperTitle, setSelectedPaperTitle] = useState<string | null>(null)

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
    fetchMaxScore()
      .then(setMaxScore)
      .catch((err) => {
        console.error("Failed to load max score:", err)
        toast({ title: "Warning", description: "Could not load score scale from server, using default.", variant: "destructive" })
      })
  }, [])

  // Auto-fetch full review data when linked directly to an expanded review
  useEffect(() => {
    if (!initialExpandedReview) return
    const controller = new AbortController()
    setLoadingFull(initialExpandedReview)
    fetch(`${API_URL}/api/reviews/${initialExpandedReview}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch review details")
        return res.json()
      })
      .then((data: FullReview) => {
        setFullReviewData((prev) => ({ ...prev, [initialExpandedReview]: data }))
      })
      .catch((err) => {
        if (err.name === "AbortError") return
        setError(err instanceof Error ? err.message : "Failed to load review details")
        setExpandedReview(null)
      })
      .finally(() => {
        setLoadingFull(null)
      })
    return () => controller.abort()
  }, [initialExpandedReview])

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

  const deleteAllReviews = async () => {
    if (!confirm("Are you sure you want to delete ALL reviews? This cannot be undone.")) {
      return
    }

    setDeletingAll(true)
    setError(null)
    try {
      const response = await fetch(`${API_URL}/api/reviews`, {
        method: "DELETE",
      })

      if (!response.ok) {
        throw new Error("Failed to delete all reviews")
      }

      await loadReviews()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete all reviews")
    } finally {
      setDeletingAll(false)
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

  const toggleExpand = async (reviewId: string) => {
    if (expandedReview === reviewId) {
      setExpandedReview(null)
      onReviewExpand?.(null)
      return
    }

    setExpandedReview(reviewId)
    onReviewExpand?.(reviewId)

    if (!fullReviewData[reviewId]) {
      setLoadingFull(reviewId)
      try {
        const response = await fetch(`${API_URL}/api/reviews/${reviewId}`)
        if (!response.ok) throw new Error("Failed to fetch review details")
        const data: FullReview = await response.json()
        setFullReviewData((prev) => ({ ...prev, [reviewId]: data }))
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load review details")
        setExpandedReview(null)
      } finally {
        setLoadingFull(null)
      }
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
          <div className="flex items-center gap-2">
            <Button
              onClick={deleteAllReviews}
              disabled={deletingAll || loading || reviews.length === 0}
              size="sm"
              variant="destructive"
            >
              {deletingAll ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              Delete All
            </Button>
            <Button onClick={loadReviews} disabled={loading} size="sm" variant="outline">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
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
          <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-md">
            <div className="text-center">
              <p className="text-2xl font-bold text-primary">{stats.total_reviews}</p>
              <p className="text-xs text-muted-foreground">Total Reviews</p>
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
                className="bg-muted rounded-md transition-colors"
              >
                <div
                  className="flex items-start justify-between p-4 hover:bg-muted/80 cursor-pointer transition-colors rounded-md"
                  onClick={() => toggleExpand(review.id)}
                >
                  <div className="flex-1 min-w-0">
                    <h3
                      className="font-semibold text-sm truncate cursor-pointer hover:text-primary hover:underline"
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedPaperTitle(review.paper_title)
                      }}
                    >
                      {review.paper_title}
                    </h3>
                    <p className="text-xs text-muted-foreground mb-2">
                      {review.pdf_filename} • {review.reviewer_model} • {formatDate(review.created_at)}
                    </p>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-semibold text-primary">
                        {review.score}/{maxScore}
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
                  <div className="flex items-center gap-1 ml-4">
                    <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
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
                    {expandedReview === review.id ? (
                      <ChevronUp className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                </div>

                {/* Expanded review details */}
                {expandedReview === review.id && (
                  <div className="px-4 pb-4 space-y-3 border-t border-border pt-4">
                    {loadingFull === review.id ? (
                      <div className="flex items-center justify-center py-4">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                      </div>
                    ) : fullReviewData[review.id] ? (
                      <>
                        <ReviewSection title="💡 Novelty" content={fullReviewData[review.id].criteria.novelty} />
                        <ReviewSection title="🔬 Methodology" content={fullReviewData[review.id].criteria.methodology} />
                        <ReviewSection title="📈 Results" content={fullReviewData[review.id].criteria.results} />
                        <ReviewSection title="✍️ Clarity" content={fullReviewData[review.id].criteria.clarity} />
                        <ReviewSection title="🎯 Impact" content={fullReviewData[review.id].criteria.impact} />
                        <ReviewSection title="💪 Strengths" content={fullReviewData[review.id].criteria.strengths} />
                        <ReviewSection title="⚠️ Limitations" content={fullReviewData[review.id].criteria.limitations} />
                        <ReviewSection title="📝 Detailed Feedback" content={fullReviewData[review.id].criteria.detailed_feedback} />
                      </>
                    ) : null}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </CardContent>

      {/* Paper reviews panel */}
      {selectedPaperTitle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setSelectedPaperTitle(null)}>
          <div className="bg-background rounded-lg shadow-xl max-w-lg w-full mx-4 p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4 gap-4">
              <div>
                <h2 className="font-semibold text-lg">Reviews for Paper</h2>
                <p className="text-sm text-muted-foreground mt-1">{selectedPaperTitle}</p>
              </div>
              <Button size="sm" variant="outline" onClick={() => setSelectedPaperTitle(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="space-y-3 max-h-[60vh] overflow-y-auto">
              {reviews
                .filter((r) => r.paper_title === selectedPaperTitle)
                .map((r) => (
                  <div key={r.id} className="p-3 bg-muted rounded-md space-y-2">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <span className="text-sm font-medium">🤖 {r.reviewer_model}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-primary">{r.score}/10</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${getRecommendationColor(r.recommendation)}`}>
                          {r.recommendation}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground font-mono break-all">ID: {r.id}</p>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
