import { QueryCache, QueryClient, queryOptions } from "@tanstack/react-query";
import { toast } from "@/hooks/use-toast";
import { api } from "./index";

declare module "@tanstack/react-query" {
  interface Register {
    queryMeta: {
      /** Shown as a toast when the query fails. Queries without it report errors where they are used. */
      errorToast?: string;
    };
  }
}

/**
 * Every backend read, as TanStack Query options. Components share a cache entry when they use the same key,
 * so e.g. the GPU monitor and the GPU load summary poll /api/gpu once, at the shorter of their intervals.
 */
export const queries = {
  maxScore: () =>
    queryOptions({
      queryKey: ["config", "maxScore"],
      queryFn: api.getMaxScore,
      staleTime: Number.POSITIVE_INFINITY,
      meta: { errorToast: "Could not load score scale from server, using default." },
    }),
  serviceConfig: () =>
    queryOptions({ queryKey: ["config", "service"], queryFn: api.getConfig, staleTime: Number.POSITIVE_INFINITY }),
  engine: () => queryOptions({ queryKey: ["engine"], queryFn: api.getEngine, staleTime: Number.POSITIVE_INFINITY }),
  conferences: () =>
    queryOptions({
      queryKey: ["conferences"],
      queryFn: api.listConferences,
      staleTime: Number.POSITIVE_INFINITY,
      select: (data) => data.conferences,
    }),
  conference: (conferenceId: string) =>
    queryOptions({
      queryKey: ["conferences", conferenceId],
      queryFn: ({ signal }) => api.getConference(conferenceId, signal),
      staleTime: Number.POSITIVE_INFINITY,
    }),
  reviewForms: () =>
    queryOptions({ queryKey: ["reviewForms", "list"], queryFn: api.listReviewForms, select: (data) => data.forms }),
  reviewForm: (formId: string) =>
    queryOptions({
      queryKey: ["reviewForms", "detail", formId],
      queryFn: ({ signal }) => api.getReviewForm(formId, signal),
      staleTime: Number.POSITIVE_INFINITY,
    }),
  installedModels: () =>
    queryOptions({
      queryKey: ["models", "installed"],
      queryFn: api.listInstalledModels,
      select: (data) => data.models,
    }),
  availableModels: () =>
    queryOptions({
      queryKey: ["models", "available"],
      queryFn: api.listAvailableModels,
      select: (data) => data.models,
    }),
  modelTags: (modelName: string) =>
    queryOptions({
      queryKey: ["models", "tags", modelName],
      queryFn: () => api.listModelTags(modelName),
      staleTime: Number.POSITIVE_INFINITY,
      select: (data) => data.tags,
    }),
  gpus: () => queryOptions({ queryKey: ["gpus"], queryFn: api.listGpus }),
  reviews: () =>
    queryOptions({ queryKey: ["reviews", "list"], queryFn: () => api.listReviews(), select: (data) => data.reviews }),
  statistics: () => queryOptions({ queryKey: ["reviews", "statistics"], queryFn: api.getStatistics }),
  review: (reviewId: string) =>
    queryOptions({
      queryKey: ["reviews", "detail", reviewId],
      queryFn: ({ signal }) => api.getReview(reviewId, signal),
      staleTime: Number.POSITIVE_INFINITY,
    }),
};

/** Cache keys to invalidate after a change, so every view of that data refetches. */
export const invalidates = {
  models: { queryKey: ["models"] },
  reviews: { queryKey: ["reviews"] },
  reviewForms: { queryKey: ["reviewForms"] },
} as const;

export function createQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => {
        const message = query.meta?.errorToast;
        if (message) toast({ title: "Warning", description: message, variant: "destructive" });
        else console.error(`Query ${JSON.stringify(query.queryKey)} failed:`, error);
      },
    }),
    defaultOptions: {
      queries: { retry: 1, refetchOnWindowFocus: false },
    },
  });
}
