import type { ReviewStatistics } from "@/lib/types";

export default function LibraryStats({ stats }: { stats: ReviewStatistics }) {
  return (
    <div className="grid grid-cols-2 gap-4 rounded-md bg-muted p-4">
      <div className="text-center">
        <p className="text-2xl font-bold text-primary">{stats.total_reviews}</p>
        <p className="text-xs text-muted-foreground">Total Reviews</p>
      </div>
      <div className="text-center">
        <p className="text-2xl font-bold text-primary">{stats.unique_papers}</p>
        <p className="text-xs text-muted-foreground">Unique Papers</p>
      </div>
    </div>
  );
}
