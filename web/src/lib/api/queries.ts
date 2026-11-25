import { MutationCache, QueryCache, QueryClient, queryOptions } from "@tanstack/react-query";
import { toast } from "@/hooks/use-toast";
import type { ReviewJob } from "@/lib/types";
import { api, UnauthorizedError } from "./index";

/** How often the review queue is read while a review is queued or running, and otherwise (others may submit). */
export const ACTIVE_QUEUE_POLL_MS = 2000;
export const IDLE_QUEUE_POLL_MS = 15000;

/** Whether a review is still waiting or running. */
export const isActiveJob = (job: Pick<ReviewJob, "status">) => job.status === "queued" || job.status === "running";

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
 * so e.g. the GPU monitor and the GPU load summary read /api/gpu once and show the same reading.
 */
export const queries = {
  /** The signed-in user, or null when nobody is: the app shows the sign-in page instead. */
  currentUser: () =>
    queryOptions({ queryKey: ["auth", "me"], queryFn: api.getCurrentUser, staleTime: Number.POSITIVE_INFINITY }),
  /**
   * The review queue: everyone's queued and running reviews and the user's finished ones. Reviews run on the server,
   * so this is how the page follows them; it is read every few seconds while one is active, rarely otherwise.
   */
  reviewJobs: () =>
    queryOptions({
      queryKey: ["reviewJobs"],
      queryFn: api.listReviewJobs,
      refetchInterval: (query) =>
        query.state.data?.jobs.some(isActiveJob) ? ACTIVE_QUEUE_POLL_MS : IDLE_QUEUE_POLL_MS,
    }),
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
  /**
   * GPU list and load. Read once and never refetched on its own: only the GPU page polls it (while open), and the
   * review page's load summary refreshes it on demand, so the GPUs are not queried while nobody looks at them.
   */
  gpus: () => queryOptions({ queryKey: ["gpus"], queryFn: api.listGpus, staleTime: Number.POSITIVE_INFINITY }),
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
  reviewJobs: { queryKey: ["reviewJobs"] },
  currentUser: { queryKey: ["auth"] },
} as const;

export function createQueryClient(): QueryClient {
  // A 401 anywhere means the sign-in expired: forget the user, so the app shows the sign-in page.
  const signedOut = (error: unknown) => {
    if (!(error instanceof UnauthorizedError)) return false;
    client.setQueryData(queries.currentUser().queryKey, null);
    return true;
  };
  const client: QueryClient = new QueryClient({
    mutationCache: new MutationCache({ onError: (error) => void signedOut(error) }),
    queryCache: new QueryCache({
      onError: (error, query) => {
        if (signedOut(error)) return;
        const message = query.meta?.errorToast;
        if (message) toast({ title: "Warning", description: message, variant: "destructive" });
        else console.error(`Query ${JSON.stringify(query.queryKey)} failed:`, error);
      },
    }),
    defaultOptions: {
      queries: {
        retry: (failures, error) => !(error instanceof UnauthorizedError) && failures < 1,
        refetchOnWindowFocus: false,
      },
    },
  });
  return client;
}
