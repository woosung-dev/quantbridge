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

export function useCreateStrategy(): UseMutationResult<
  StrategyResponse,
  Error,
  CreateStrategyRequest
> {
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
    },
  });
}

export function useUpdateStrategy(
  id: string,
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
    },
  });
}

export function useDeleteStrategy(): UseMutationResult<void, Error, string> {
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
    },
  });
}

export function useParseStrategy(): UseMutationResult<
  ParsePreviewResponse,
  Error,
  string
> {
  const { getToken } = useAuth();
  return useMutation({
    mutationFn: async (pine_source: string) => {
      const token = await getToken();
      return parseStrategy(pine_source, token);
    },
  });
}
