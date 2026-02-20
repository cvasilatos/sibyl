"use client"

import React, { createContext, useContext, useState, useRef, useEffect, ReactNode } from 'react'
import { API_URL } from '@/lib/config'

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
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const clearError = () => setError(null)

  // Clean up polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current !== null) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

  const startDownload = (
    modelName: string,
    onComplete: () => void,
    onError: (message: string) => void,
    onProgress?: (progress: number, message: string) => void
  ) => {
    setInstalling(modelName)
    setDownloadProgress(0)
    setError(null)

    // Start the pull job via REST
    fetch(`${API_URL}/api/models/pull?model_name=${encodeURIComponent(modelName)}`, { method: "POST" })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to start model pull")
        return res.json()
      })
      .then(({ pull_id }: { pull_id: string }) => {
        // Poll for status
        pollIntervalRef.current = setInterval(async () => {
          try {
            const statusRes = await fetch(`${API_URL}/api/models/pull/${pull_id}`)
            if (!statusRes.ok) throw new Error("Failed to get pull status")
            const data = await statusRes.json()

            const progress = data.progress ?? 0
            setDownloadProgress(progress)
            if (onProgress) onProgress(progress, data.status)

            if (data.status === "success") {
              clearInterval(pollIntervalRef.current!)
              pollIntervalRef.current = null
              setInstalling(null)
              setDownloadProgress(0)
              onComplete()
            } else if (data.status === "error") {
              clearInterval(pollIntervalRef.current!)
              pollIntervalRef.current = null
              const msg = data.message || "Model pull failed"
              setError(msg)
              setInstalling(null)
              setDownloadProgress(0)
              onError(msg)
            }
          } catch (e) {
            clearInterval(pollIntervalRef.current!)
            pollIntervalRef.current = null
            const msg = e instanceof Error ? e.message : "Failed to poll pull status"
            setError(msg)
            setInstalling(null)
            setDownloadProgress(0)
            onError(msg)
          }
        }, 1000)
      })
      .catch((err) => {
        const msg = err instanceof Error ? err.message : "Failed to install model"
        setError(msg)
        setInstalling(null)
        setDownloadProgress(0)
        onError(msg)
      })
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