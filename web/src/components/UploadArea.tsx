import { FileText, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import type { RefObject } from "react"

type Props = {
  selectedFile: File | null
  selectedModel: string
  availableModels: string[]
  onModelChange: (model: string) => void
  fileInputRef: RefObject<HTMLInputElement>
  isDragging: boolean
  handleDragOver: (e: React.DragEvent) => void
  handleDragLeave: (e: React.DragEvent) => void
  handleDrop: (e: React.DragEvent) => void
  handleFileInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  startReview: () => Promise<void>
  isReviewing: boolean
  progress: number
  progressMessage: string
  error: string | null
}

export default function UploadArea({
  selectedFile,
  selectedModel,
  availableModels,
  onModelChange,
  fileInputRef,
  isDragging,
  handleDragOver,
  handleDragLeave,
  handleDrop,
  handleFileInputChange,
  startReview,
  isReviewing,
  progress,
  progressMessage,
  error,
}: Props) {
  return (
    <>
      <div
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-all ${
          isDragging ? "border-primary bg-primary/5 scale-[1.02]" : "border-border hover:border-primary hover:bg-accent"
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
          {selectedFile ? `Selected: ${selectedFile.name}` : "Drag and drop a PDF file here or click to browse"}
        </p>
        <p className="text-sm text-muted-foreground">
          {selectedFile ? `Size: ${(selectedFile.size / 1024 / 1024).toFixed(2)} MB` : "Supports research papers in PDF format"}
        </p>
      </div>

      {/* Model selection */}
      {availableModels.length > 0 && (
        <div className="space-y-2">
          <label className="text-sm font-medium">Select Model for Review</label>
          <select
            value={selectedModel}
            onChange={(e) => onModelChange(e.target.value)}
            disabled={isReviewing}
            className="w-full px-3 py-2 text-sm border border-input rounded-md bg-background"
          >
            {availableModels.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground">
            This will override the default model configured in your environment
          </p>
        </div>
      )}

      <Button onClick={startReview} disabled={!selectedFile || isReviewing} className="w-full" size="lg">
        <Upload className="mr-2 h-4 w-4" />
        {isReviewing ? "Reviewing..." : "Start Review"}
      </Button>

      {isReviewing && (
        <div className="space-y-2">
          <Progress value={progress} className="h-2" />
          <p className="text-sm text-center text-muted-foreground">{progressMessage} ({progress}%)</p>
        </div>
      )}

      {error && (
        <Card className="border-destructive">
          <CardContent className="p-4">
            <p className="text-destructive">❌ Error: {error}</p>
          </CardContent>
        </Card>
      )}
    </>
  )
}
