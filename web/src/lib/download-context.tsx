"use client"

import React, { createContext, useContext, useState, ReactNode } from 'react'
import { API_URL, getWebSocketUrl } from '@/lib/config'

interface DownloadProgress {
  model_name: string
  status: string
  progress: number
  message: string
  total: number
  completed: number
}

interface DownloadContextType {
  installing: string | null
  downloadProgress: number
  error: string | null
  startDownload: (modelName: string, onComplete: () => void, onError: (message: string) => void, onProgress?: (progress: number, message: string) => void) => void
  clearError: () => void
}

const DownloadContext = createContext<DownloadContextType | undefined>(undefined)

export function DownloadProvider({ children }: { children: ReactNode }) {
  const [installing, setInstalling] = useState<string | null>(null)
  const [downloadProgress, setDownloadProgress] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)

  const clearError = () => setError(null)

  const startDownload = (
    modelName: string,
    onComplete: () => void,
    onError: (message: string) => void,
    onProgress?: (progress: number, message: string) => void
  ) => {
    setInstalling(modelName)
    setDownloadProgress(0)
    setError(null)

    try {
      const wsBaseUrl = getWebSocketUrl()
      // Connect to the new pull endpoint with model_name as a query parameter
      const ws = new WebSocket(`${wsBaseUrl}/ws/pull?model_name=${encodeURIComponent(modelName)}`)
      let isFinished = false

      ws.onopen = () => {
        console.log(`Connected to pull stream for ${modelName}`)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.status === "error") {
             isFinished = true
             ws.close()
             setError(data.message)
             setInstalling(null)
             setDownloadProgress(0)
             onError(data.message)
             return
          }

          let progress = 0
          if (data.total && data.completed) {
            progress = Math.round((data.completed / data.total) * 100)
            setDownloadProgress(progress)
            if (onProgress) onProgress(progress, data.status)
          } else {
             if (onProgress) onProgress(downloadProgress, data.status)
          }

          if (data.status === "success") {
            isFinished = true
            ws.close()
            setInstalling(null)
            setDownloadProgress(0)
            onComplete()
          }
        } catch (e) {
          console.error("Error parsing websocket message:", e)
        }
      }

      ws.onerror = (e) => {
        console.error("WebSocket error:", e)
        if (!isFinished) {
          setError("WebSocket connection failed")
          setInstalling(null)
          setDownloadProgress(0)
          onError("Failed to connect to download stream")
        }
      }

      ws.onclose = (e) => {
        if (!isFinished) {
           console.log("WebSocket closed unexpectedly")
           setError("Connection lost during download")
           setInstalling(null)
           setDownloadProgress(0)
           onError("Connection lost during model download")
        }
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to install model")
      setInstalling(null)
      setDownloadProgress(0)
      onError(err instanceof Error ? err.message : "Failed to start model installation")
    }
  }

  return (
    <DownloadContext.Provider value={{
      installing,
      downloadProgress,
      error,
      startDownload,
      clearError
    }}>
      {children}
    </DownloadContext.Provider>
  )
}

export function useDownload() {
  const context = useContext(DownloadContext)
  if (context === undefined) {
    throw new Error('useDownload must be used within a DownloadProvider')
  }
  return context
}