"use client";

// Sprint 7c: Strategy React Query 훅 — Clerk JWT 자동 주입 + invalidate/setQueryData 패턴.
// frontend.md §3.2 — Query Key 하드코딩 금지 → 도메인 팩토리(strategyKeys).

import { useAuth } from "@clerk/nextjs";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  createStrategy,
  deleteStrategy,
  getStrategy,
  listStrategies,
  parseStrategy,
  updateStrategy,
} from "./api";
import type {
  CreateStrategyRequest,
  ParsePreviewResponse,
  StrategyListQuery,
  StrategyListResponse,
  StrategyResponse,
  UpdateStrategyRequest,
} from "./schemas";

export const strategyKeys = {
  all: ["strategies"] as const,
  lists: () => [...strategyKeys.all, "list"] as const,
  list: (query: StrategyListQuery) => [...strategyKeys.lists(), query] as const,
  details: () => [...strategyKeys.all, "detail"] as const,
  detail: (id: string) => [...strategyKeys.details(), id] as const,
  parse: () => [...strategyKeys.all, "parse"] as const,
};

export function useStrategies(
  query: StrategyListQuery,
): UseQueryResult<StrategyListResponse, Error> {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: strategyKeys.list(query),
    queryFn: async () => {
      const token = await getToken();
      return listStrategies(query, token);
    },
  });
}

export function useStrategy(
  id: string | undefined,
): UseQueryResult<StrategyResponse, Error> {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: id ? strategyKeys.detail(id) : strategyKeys.details(),
    queryFn: async () => {
      if (!id) throw new Error("strategy id is required");
      const token = await getToken();
      return getStrategy(id, token);
    },
    enabled: Boolean(id),
  });
}

// T5에서 추가된 hook-level callback 옵션. cache invalidation은 내부에서 유지하고,
// 호출부의 UX 반응(toast, dialog phase 전환 등)만 선택적으로 주입.
export interface MutationCallbacks<TData, TError = Error> {
  onSuccess?: (data: TData) => void;
  onError?: (err: TError) => void;
}

export function useCreateStrategy(
  opts: MutationCallbacks<StrategyResponse> = {},
): UseMutationResult<StrategyResponse, Error, CreateStrategyRequest> {
  const { getToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: CreateStrategyRequest) => {
      const token = await getToken();
      return createStrategy(body, token);
    },
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: strategyKeys.lists() });
      qc.setQueryData(strategyKeys.detail(created.id), created);
      opts.onSuccess?.(created);
    },
    onError: (err) => opts.onError?.(err),
  });
}

export function useUpdateStrategy(
  id: string,
  opts: MutationCallbacks<StrategyResponse> = {},
): UseMutationResult<StrategyResponse, Error, UpdateStrategyRequest> {
  const { getToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: UpdateStrategyRequest) => {
      const token = await getToken();
      return updateStrategy(id, body, token);
    },
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: strategyKeys.lists() });
      qc.setQueryData(strategyKeys.detail(updated.id), updated);
      opts.onSuccess?.(updated);
    },
    onError: (err) => opts.onError?.(err),
  });
}

export function useDeleteStrategy(
  opts: MutationCallbacks<void> = {},
): UseMutationResult<void, Error, string> {
  const { getToken } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      return deleteStrategy(id, token);
    },
    onSuccess: (_void, id) => {
      qc.invalidateQueries({ queryKey: strategyKeys.lists() });
      qc.removeQueries({ queryKey: strategyKeys.detail(id) });
      opts.onSuccess?.();
    },
    onError: (err) => opts.onError?.(err),
  });
}

export function useParseStrategy(
  opts: MutationCallbacks<ParsePreviewResponse> = {},
): UseMutationResult<ParsePreviewResponse, Error, string> {
  const { getToken } = useAuth();
  return useMutation({
    mutationFn: async (pine_source: string) => {
      const token = await getToken();
      return parseStrategy(pine_source, token);
    },
    onSuccess: (data) => opts.onSuccess?.(data),
    onError: (err) => opts.onError?.(err),
  });
}
