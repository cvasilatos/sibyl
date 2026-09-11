import { BookOpen, FileText, Monitor, Settings } from "lucide-react";
import Link from "next/link";
import type { AppTab } from "@/lib/types";

type Props = {
  activeTab: AppTab;
};

export default function Tabs({ activeTab }: Props) {
  return (
    <div className="flex gap-6 sm:gap-12">
      <Link
        href="/?tab=review"
        className={`pb-6 px-2 text-sm font-medium transition-colors relative ${activeTab === "review" ? "text-primary" : "text-muted-foreground hover:text-foreground"}`}
      >
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          <span>Review Paper</span>
        </div>
        {activeTab === "review" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
      </Link>

      <Link
        href="/?tab=library"
        className={`pb-6 px-2 text-sm font-medium transition-colors relative ${activeTab === "library" ? "text-primary" : "text-muted-foreground hover:text-foreground"}`}
      >
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4" />
          <span>Library</span>
        </div>
        {activeTab === "library" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
      </Link>

      <Link
        href="/?tab=models"
        className={`pb-6 px-2 text-sm font-medium transition-colors relative ${activeTab === "models" ? "text-primary" : "text-muted-foreground hover:text-foreground"}`}
      >
        <div className="flex items-center gap-2">
          <Settings className="h-4 w-4" />
          <span>Models</span>
        </div>
        {activeTab === "models" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
      </Link>

      <Link
        href="/?tab=gpu"
        className={`pb-6 px-2 text-sm font-medium transition-colors relative ${activeTab === "gpu" ? "text-primary" : "text-muted-foreground hover:text-foreground"}`}
      >
        <div className="flex items-center gap-2">
          <Monitor className="h-4 w-4" />
          <span>GPU</span>
        </div>
        {activeTab === "gpu" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
      </Link>
    </div>
  );
}
