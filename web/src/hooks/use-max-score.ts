import { useQuery } from "@tanstack/react-query";
import { queries } from "@/lib/api/queries";

const DEFAULT_MAX_SCORE = 10;

/** The top of the overall score scale, loaded once per session. Falls back to 10 until (or unless) the server answers. */
export function useMaxScore(): number {
  return useQuery(queries.maxScore()).data ?? DEFAULT_MAX_SCORE;
}
