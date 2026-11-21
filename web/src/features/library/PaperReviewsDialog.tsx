import RecommendationBadge from "@/components/RecommendationBadge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { StoredReview } from "@/lib/types";

type Props = {
  /** The paper whose reviews to list, or null when the dialog is closed. */
  paperTitle: string | null;
  reviews: StoredReview[];
  maxScore: number;
  onClose: () => void;
};

/** Every stored review of one paper, by model. */
export default function PaperReviewsDialog({ paperTitle, reviews, maxScore, onClose }: Props) {
  return (
    <Dialog open={paperTitle !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reviews for Paper</DialogTitle>
          <DialogDescription>{paperTitle}</DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] space-y-3 overflow-y-auto">
          {reviews
            .filter((r) => r.paper_title === paperTitle)
            .map((r) => (
              <div key={r.id} className="space-y-2 rounded-md bg-muted p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium">🤖 {r.reviewer_model}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-primary">
                      {r.score}/{maxScore}
                    </span>
                    <RecommendationBadge recommendation={r.recommendation} />
                  </div>
                </div>
                <p className="break-all font-mono text-xs text-muted-foreground">ID: {r.id}</p>
              </div>
            ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
