/**
 * Configuration for the Sibyl application.
 * Uses Next.js environment variables for configuration.
 */

/**
 * Get the backend API URL from environment variables or use default.
 * In Next.js, environment variables must be prefixed with NEXT_PUBLIC_ to be accessible in the browser.
 */
export const API_URL: string = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

/**
 * Get the WebSocket URL from the API URL.
 * Converts http:// to ws:// and https:// to wss://
 */
export function getWebSocketUrl(): string {
  const url = new URL(API_URL)
  const protocol = url.protocol === "https:" ? "wss:" : "ws:"
  return `${protocol}//${url.host}`
}

/**
 * Fetch the maximum review score from the backend configuration endpoint.
 */
export async function fetchMaxScore(): Promise<number> {
  const response = await fetch(`${API_URL}/api/config`)
  if (!response.ok) {
    throw new Error("Failed to fetch config")
  }
  const data = await response.json()
  const maxScore = data.max_score
  if (typeof maxScore !== "number" || maxScore <= 0) {
    throw new Error("Invalid max_score in config response")
  }
  return maxScore
}
