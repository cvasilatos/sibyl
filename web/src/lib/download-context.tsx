"use client"

import React, { createContext, useContext, useState, ReactNode } from 'react'
import { getWebSocketUrl } from '@/lib/config'

interface DownloadContextType {
  installing: string[]
  downloadProgresses: Record<string, number>
  error: string | null
  startDownload: (modelName: string, onComplete: () => void, onError: (message: string) => void, onProgress?: (progress: number, message: string) => void) => void
  clearError: () => void
}

const DownloadContext = createContext<DownloadContextType | undefined>(undefined)

export function DownloadProvider({ children }: { children: ReactNode }) {
  const [installing, setInstalling] = useState<string[]>([])
  const [downloadProgresses, setDownloadProgresses] = useState<Record<string, number>>({})
  const [error, setError] = useState<string | null>(null)

  const clearError = () => setError(null)

  const startDownload = (
    modelName: string,
    onComplete: () => void,
    onError: (message: string) => void,
    onProgress?: (progress: number, message: string) => void
  ) => {
    setInstalling(prev => [...prev, modelName])
    setDownloadProgresses(prev => ({ ...prev, [modelName]: 0 }))
    setError(null)

    const removeModel = () => {
      setInstalling(prev => prev.filter(m => m !== modelName))
      setDownloadProgresses(prev => {
        const next = { ...prev }
        delete next[modelName]
        return next
      })
    }

    try {
      const wsBaseUrl = getWebSocketUrl()
      const ws = new WebSocket(`${wsBaseUrl}/ws/pull?model_name=${encodeURIComponent(modelName)}`)
      let isFinished = false
      let currentProgress = 0

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
            removeModel()
            onError(data.message)
            return
          }

          if (data.total && data.completed) {
            currentProgress = Math.round((data.completed / data.total) * 100)
            setDownloadProgresses(prev => ({ ...prev, [modelName]: currentProgress }))
            if (onProgress) onProgress(currentProgress, data.status)
          } else {
            if (onProgress) onProgress(currentProgress, data.status)
          }

          if (data.status === "success") {
            isFinished = true
            ws.close()
            removeModel()
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
          removeModel()
          onError("Failed to connect to download stream")
        }
      }

      ws.onclose = () => {
        if (!isFinished) {
          console.log("WebSocket closed unexpectedly")
          setError("Connection lost during download")
          removeModel()
          onError("Connection lost during model download")
        }
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to install model")
      removeModel()
      onError(err instanceof Error ? err.message : "Failed to start model installation")
    }
  }

  return (
    <DownloadContext.Provider value={{
      installing,
      downloadProgresses,
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