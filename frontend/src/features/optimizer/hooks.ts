"use client";

// Optimizer React Query hooks — Clerk JWT + userId factory pattern (LESSON-005).
// polling refetchInterval = RUNNING/QUEUED 시 2s, COMPLETED/FAILED 시 false (LESSON-004 CPU 보호).

import { useAuth } from "@clerk/nextjs";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type Query,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  getOptimizationRun,
  listOptimizationRuns,
  postGridSearch,
} from "./api";
import {
  optimizerKeys,
  type OptimizationRunListQuery,
} from "./query-keys";
import type {
  CreateOptimizationRunRequest,
  OptimizationRunListResponse,
  OptimizationRunResponse,
} from "./schemas";

export { optimizerKeys };

const ANON_USER_ID = "anon";

function makeRunListFetcher(query: OptimizationRunListQuery, getToken: () => Promise<string | null>) {
  return async () => listOptimizationRuns(query, await getToken());
}

function makeRunDetailFetcher(id: string, getToken: () => Promise<string | null>) {
  return async () => getOptimizationRun(id, await getToken());
}

export function useOptimizationRuns(
  query: OptimizationRunListQuery,
): UseQueryResult<OptimizationRunListResponse> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: optimizerKeys.list(uid, query),
    queryFn: makeRunListFetcher(query, getToken),
    enabled: userId != null,
  });
}

export function useOptimizationRun(
  id: string | null,
): UseQueryResult<OptimizationRunResponse> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: optimizerKeys.detail(uid, id ?? "none"),
    queryFn: makeRunDetailFetcher(id ?? "", getToken),
    enabled: userId != null && id != null,
    // LESSON-004: status QUEUED/RUNNING 시 2s polling, 종료 status 시 false.
    refetchInterval: (q: Query<OptimizationRunResponse>) => {
      if (q.state.error) return false;
      const status = q.state.data?.status;
      if (status === "queued" || status === "running") return 2000;
      return false;
    },
  });
}

export function useSubmitGridSearch(): UseMutationResult<
  OptimizationRunResponse,
  Error,
  CreateOptimizationRunRequest
> {
  const { userId, getToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => postGridSearch(body, await getToken()),
    onSuccess: () => {
      const uid = userId ?? ANON_USER_ID;
      void queryClient.invalidateQueries({ queryKey: optimizerKeys.all(uid) });
    },
  });
}
