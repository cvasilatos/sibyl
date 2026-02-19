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
