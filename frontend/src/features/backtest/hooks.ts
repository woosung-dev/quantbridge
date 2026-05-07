"use client";

// Sprint FE-04: Backtest React Query hooks — Clerk JWT + userId factory pattern.
// LESSON-005: queryKey factory `backtestKeys.list(userId, query)` — userId 첫 인자.
//            queryFn은 모듈-level `makeXxxFetcher(...)` CallExpression 으로 @tanstack/query/exhaustive-deps 우회.
// LESSON-004: polling refetchInterval은 error 시 false — 무한 루프/CPU 100% 방지.

import { useAuth } from "@clerk/nextjs";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
  type Query,
} from "@tanstack/react-query";

import {
  cancelBacktest,
  createBacktest,
  createBacktestShare,
  deleteBacktest,
  getBacktest,
  getBacktestProgress,
  getStressTest,
  listBacktests,
  listBacktestTrades,
  postMonteCarlo,
  postWalkForward,
  revokeBacktestShare,
} from "./api";
import {
  backtestKeys,
  stressTestKeys,
  type BacktestListQuery,
  type BacktestTradesQuery,
} from "./query-keys";
import type {
  BacktestCancelResponse,
  BacktestCreatedResponse,
  BacktestDetail,
  BacktestListResponse,
  BacktestProgressResponse,
  CreateBacktestRequest,
  CreateMonteCarloRequest,
  CreateWalkForwardRequest,
  ShareTokenResponse,
  StressTestCreatedResponse,
  StressTestDetail,
  TradeListResponse,
} from "./schemas";

export { backtestKeys, stressTestKeys };

const ANON_USER_ID = "anon";

const POLL_INTERVAL_MS = 30_000;

type TokenGetter = () => Promise<string | null>;

// --- queryFn factories (module-level, CallExpression at call site) ---------

function makeListFetcher(query: BacktestListQuery, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return listBacktests(query, token);
  };
}

function makeDetailFetcher(id: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return getBacktest(id, token);
  };
}

function makeProgressFetcher(id: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return getBacktestProgress(id, token);
  };
}

function makeTradesFetcher(
  id: string,
  query: BacktestTradesQuery,
  getToken: TokenGetter,
) {
  return async () => {
    const token = await getToken();
    return listBacktestTrades(id, query, token);
  };
}

// --- polling interval — LESSON-004 guard ---------------------------------

function progressRefetchInterval(
  q: Query<BacktestProgressResponse, Error>,
): number | false {
  if (q.state.status === "error") return false;
  const data = q.state.data;
  if (data == null) return POLL_INTERVAL_MS;
  if (
    data.status === "completed" ||
    data.status === "failed" ||
    data.status === "cancelled"
  ) {
    return false;
  }
  return POLL_INTERVAL_MS;
}

// --- Mutation callback opts ----------------------------------------------

export interface MutationCallbacks<TData, TError = Error> {
  onSuccess?: (data: TData) => void;
  onError?: (err: TError) => void;
}

// --- Hooks ---------------------------------------------------------------

export function useBacktests(
  query: BacktestListQuery,
): UseQueryResult<BacktestListResponse, Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: backtestKeys.list(uid, query),
    queryFn: makeListFetcher(query, getToken),
  });
}

export function useBacktest(
  id: string | undefined,
): UseQueryResult<BacktestDetail, Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: id ? backtestKeys.detail(uid, id) : backtestKeys.details(uid),
    queryFn: makeDetailFetcher(id ?? "", getToken),
    enabled: Boolean(id),
  });
}

export function useBacktestProgress(
  id: string | undefined,
): UseQueryResult<BacktestProgressResponse, Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: id ? backtestKeys.progress(uid, id) : backtestKeys.all(uid),
    queryFn: makeProgressFetcher(id ?? "", getToken),
    enabled: Boolean(id),
    refetchInterval: progressRefetchInterval,
    refetchIntervalInBackground: false,
  });
}

export function useBacktestTrades(
  id: string | undefined,
  query: BacktestTradesQuery,
  options: { enabled?: boolean } = {},
): UseQueryResult<TradeListResponse, Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: id
      ? backtestKeys.trades(uid, id, query)
      : backtestKeys.all(uid),
    queryFn: makeTradesFetcher(id ?? "", query, getToken),
    enabled: Boolean(id) && (options.enabled ?? true),
  });
}

export function useCreateBacktest(
  opts: MutationCallbacks<BacktestCreatedResponse> = {},
): UseMutationResult<BacktestCreatedResponse, Error, CreateBacktestRequest> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: CreateBacktestRequest) => {
      const token = await getToken();
      return createBacktest(body, token);
    },
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: backtestKeys.lists(uid) });
      opts.onSuccess?.(created);
    },
    onError: (err) => opts.onError?.(err),
  });
}

export function useCancelBacktest(
  opts: MutationCallbacks<BacktestCancelResponse> = {},
): UseMutationResult<BacktestCancelResponse, Error, string> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      return cancelBacktest(id, token);
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: backtestKeys.lists(uid) });
      qc.invalidateQueries({
        queryKey: backtestKeys.detail(uid, res.backtest_id),
      });
      qc.invalidateQueries({
        queryKey: backtestKeys.progress(uid, res.backtest_id),
      });
      opts.onSuccess?.(res);
    },
    onError: (err) => opts.onError?.(err),
  });
}

export function useDeleteBacktest(
  opts: MutationCallbacks<void> = {},
): UseMutationResult<void, Error, string> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      return deleteBacktest(id, token);
    },
    onSuccess: (_void, id) => {
      qc.invalidateQueries({ queryKey: backtestKeys.lists(uid) });
      qc.removeQueries({ queryKey: backtestKeys.detail(uid, id) });
      qc.removeQueries({ queryKey: backtestKeys.progress(uid, id) });
      opts.onSuccess?.();
    },
    onError: (err) => opts.onError?.(err),
  });
}

// --- Sprint 41 Worker H — share link (LESSON-004/005/006 정합) -------------

export function useCreateBacktestShare(
  opts: MutationCallbacks<ShareTokenResponse> = {},
): UseMutationResult<ShareTokenResponse, Error, string> {
  const { getToken } = useAuth();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      return createBacktestShare(id, token);
    },
    onSuccess: (res) => opts.onSuccess?.(res),
    onError: (err) => opts.onError?.(err),
  });
}

export function useRevokeBacktestShare(
  opts: MutationCallbacks<void> = {},
): UseMutationResult<void, Error, string> {
  const { getToken } = useAuth();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      return revokeBacktestShare(id, token);
    },
    onSuccess: () => opts.onSuccess?.(),
    onError: (err) => opts.onError?.(err),
  });
}

// --- Stress Test (Phase C) -----------------------------------------------

const STRESS_TEST_POLL_MS = 2_000;

// queryFn factory — 모듈 레벨 CallExpression 으로 @tanstack/query/exhaustive-deps 우회.
function makeStressTestFetcher(id: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return getStressTest(id, token);
  };
}

// LESSON-004 guard: refetchInterval 은 module-level 순수 함수로, terminal status 에서 false 반환.
// React Query data 객체를 useEffect dep 로 쓰지 않아 CPU 100% 루프를 원천 차단.
export function stressTestRefetchInterval(
  q: Query<StressTestDetail, Error>,
): number | false {
  if (q.state.status === "error") return false;
  const data = q.state.data;
  if (data == null) return STRESS_TEST_POLL_MS;
  if (data.status === "completed" || data.status === "failed") {
    return false;
  }
  return STRESS_TEST_POLL_MS;
}

export function useCreateMonteCarlo(
  opts: MutationCallbacks<StressTestCreatedResponse> = {},
): UseMutationResult<StressTestCreatedResponse, Error, CreateMonteCarloRequest> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: CreateMonteCarloRequest) => {
      const token = await getToken();
      return postMonteCarlo(body, token);
    },
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: stressTestKeys.all(uid) });
      opts.onSuccess?.(created);
    },
    onError: (err) => opts.onError?.(err),
  });
}

export function useCreateWalkForward(
  opts: MutationCallbacks<StressTestCreatedResponse> = {},
): UseMutationResult<StressTestCreatedResponse, Error, CreateWalkForwardRequest> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: CreateWalkForwardRequest) => {
      const token = await getToken();
      return postWalkForward(body, token);
    },
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: stressTestKeys.all(uid) });
      opts.onSuccess?.(created);
    },
    onError: (err) => opts.onError?.(err),
  });
}

export function useStressTest(
  id: string | null,
): UseQueryResult<StressTestDetail, Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: id
      ? stressTestKeys.detail(uid, id)
      : stressTestKeys.all(uid),
    queryFn: makeStressTestFetcher(id ?? "", getToken),
    enabled: Boolean(id),
    refetchInterval: stressTestRefetchInterval,
    refetchIntervalInBackground: false,
  });
}
