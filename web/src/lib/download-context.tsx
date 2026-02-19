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

  const startDownload = async (
    modelName: string,
    onComplete: () => void,
    onError: (message: string) => void,
    onProgress?: (progress: number, message: string) => void
  ) => {
    setInstalling(modelName)
    setDownloadProgress(0)
    setError(null)

    try {
      // Start the download
      const response = await fetch(`${API_URL}/api/models/download`, {
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

      // Connect to WebSocket for progress updates
      const wsBaseUrl = getWebSocketUrl()
      const ws = new WebSocket(`${wsBaseUrl}/ws/models/download/${downloadId}`)

      ws.onmessage = (event) => {
        const progress: DownloadProgress = JSON.parse(event.data)
        setDownloadProgress(progress.progress)

        if (onProgress) {
          onProgress(progress.progress, progress.message)
        }

        if (progress.status === "completed") {
          ws.close()
          setInstalling(null)
          setDownloadProgress(0)
          onComplete()
        } else if (progress.status === "error") {
          ws.close()
          setError(progress.message)
          setInstalling(null)
          setDownloadProgress(0)
          onError(progress.message)
        }
      }

      ws.onerror = () => {
        setError("WebSocket connection failed")
        setInstalling(null)
        setDownloadProgress(0)
        onError("Failed to connect to download progress stream")
      }

      ws.onclose = () => {
        if (installing) {
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