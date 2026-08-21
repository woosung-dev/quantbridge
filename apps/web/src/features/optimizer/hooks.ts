// 옵티마이저 React Query 훅 — Clerk JWT + userId 팩토리 패턴(LESSON-005). 조회는
// useOptimizationRuns/useOptimizationRun, 변이는 useSubmitGridSearch/useSubmitBayesianSearch/
// useSubmitGeneticSearch(그리드서치·베이지안·유전 알고리즘 실행 제출) 훅으로 나눠 내보낸다.
"use client";

// polling refetchInterval = RUNNING/QUEUED 시 2s, COMPLETED/FAILED 시 false (LESSON-004 CPU 보호).

import { useQuery, type UseMutationResult, type UseQueryResult } from "@tanstack/react-query";

import { useAuthCtx } from "@/hooks/use-auth-ctx";
import { useInvalidatingMutation } from "@/hooks/use-invalidating-mutation";
import { makeRefetchInterval } from "@/lib/query-poll";

import {
  getOptimizationRun,
  listOptimizationRuns,
  postBayesianSearch,
  postGeneticSearch,
  postGridSearch,
} from "./api";
import { optimizerKeys, type OptimizationRunListQuery } from "./query-keys";
import type {
  CreateOptimizationRunRequest,
  OptimizationRunListResponse,
  OptimizationRunResponse,
} from "./schemas";

export { optimizerKeys };

// LESSON-004: status QUEUED/RUNNING 시 2s polling, 종료 status/data 미도착 시 false.
// (기존 `q.state.error` 가드는 다른 도메인과 동일한 status 기반 가드로 통일 — makeRefetchInterval.)
const runDetailRefetchInterval = makeRefetchInterval<OptimizationRunResponse>((data) => {
  const status = data?.status;
  return status === "queued" || status === "running" ? 2_000 : false;
});

function makeRunListFetcher(
  query: OptimizationRunListQuery,
  getToken: () => Promise<string | null>,
) {
  return async () => listOptimizationRuns(query, await getToken());
}

function makeRunDetailFetcher(id: string, getToken: () => Promise<string | null>) {
  return async () => getOptimizationRun(id, await getToken());
}

export function useOptimizationRuns(
  query: OptimizationRunListQuery,
): UseQueryResult<OptimizationRunListResponse> {
  const { uid, userId, getToken } = useAuthCtx();
  return useQuery({
    queryKey: optimizerKeys.list(uid, query),
    queryFn: makeRunListFetcher(query, getToken),
    enabled: userId != null,
  });
}

export function useOptimizationRun(id: string | null): UseQueryResult<OptimizationRunResponse> {
  const { uid, userId, getToken } = useAuthCtx();
  return useQuery({
    queryKey: optimizerKeys.detail(uid, id ?? "none"),
    queryFn: makeRunDetailFetcher(id ?? "", getToken),
    enabled: userId != null && id != null,
    refetchInterval: runDetailRefetchInterval,
  });
}

export function useSubmitGridSearch(): UseMutationResult<
  OptimizationRunResponse,
  Error,
  CreateOptimizationRunRequest
> {
  return useInvalidatingMutation({
    mutationFn: (body: CreateOptimizationRunRequest, token) => postGridSearch(body, token),
    invalidateKeys: (uid) => [optimizerKeys.all(uid)],
  });
}

// Sprint 55 — Bayesian executor submit mutation (ADR-013 §6 #5).
export function useSubmitBayesianSearch(): UseMutationResult<
  OptimizationRunResponse,
  Error,
  CreateOptimizationRunRequest
> {
  return useInvalidatingMutation({
    mutationFn: (body: CreateOptimizationRunRequest, token) => postBayesianSearch(body, token),
    invalidateKeys: (uid) => [optimizerKeys.all(uid)],
  });
}

// Sprint 56 — Genetic executor submit mutation (BL-233, Bayesian 패턴 mirror).
export function useSubmitGeneticSearch(): UseMutationResult<
  OptimizationRunResponse,
  Error,
  CreateOptimizationRunRequest
> {
  return useInvalidatingMutation({
    mutationFn: (body: CreateOptimizationRunRequest, token) => postGeneticSearch(body, token),
    invalidateKeys: (uid) => [optimizerKeys.all(uid)],
  });
}
