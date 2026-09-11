export function recommendationClassName(recommendation: string): string {
  const normalized = recommendation.toLowerCase();
  if (normalized.includes("accept")) return "text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-950";
  if (normalized.includes("reject")) return "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950";
  return "text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-950";
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString();
}
