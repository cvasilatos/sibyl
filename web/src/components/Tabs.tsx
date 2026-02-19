import { BookOpen, FileText, Settings } from "lucide-react"

type Props = {
  activeTab: "review" | "library" | "models"
  setActiveTab: (t: "review" | "library" | "models") => void
}

export default function Tabs({ activeTab, setActiveTab }: Props) {
  return (
    <div className="flex gap-4">
      <button
        onClick={() => setActiveTab("review")}
        className={`pb-3 px-2 text-sm font-medium transition-colors relative ${
          activeTab === "review" ? "text-primary" : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          <span>Review Paper</span>
        </div>
        {activeTab === "review" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
      </button>

      <button
        onClick={() => setActiveTab("library")}
        className={`pb-3 px-2 text-sm font-medium transition-colors relative ${
          activeTab === "library" ? "text-primary" : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4" />
          <span>Library</span>
        </div>
        {activeTab === "library" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
      </button>

      <button
        onClick={() => setActiveTab("models")}
        className={`pb-3 px-2 text-sm font-medium transition-colors relative ${
          activeTab === "models" ? "text-primary" : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <div className="flex items-center gap-2">
          <Settings className="h-4 w-4" />
          <span>Models</span>
        </div>
        {activeTab === "models" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
      </button>
    </div>
  )
}
