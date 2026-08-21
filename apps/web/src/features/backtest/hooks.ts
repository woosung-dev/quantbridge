// Sprint FE-04: 백테스트 React Query 훅 — Clerk JWT + userId 팩토리 패턴(LESSON-005).
// 조회는 useBacktests/useBacktest/useBacktestProgress/useBacktestTrades/useAllBacktestTrades 등,
// 변이는 useCreateBacktest/useCancelBacktest/useDeleteBacktest 와 스트레스 테스트
// (useCreateMonteCarlo/useCreateWalkForward/useCreateCostAssumption/useCreateParamStability) 훅으로
// 나눠 내보낸다.
"use client";

// LESSON-005: queryKey factory `backtestKeys.list(userId, query)` — userId 첫 인자.
//            queryFn은 모듈-level `makeXxxFetcher(...)` CallExpression 으로 @tanstack/query/exhaustive-deps 우회.
// LESSON-004: polling refetchInterval은 error 시 false — 무한 루프/CPU 100% 방지.

import {
  useMutation,
  useQuery,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { useAuthCtx, type TokenGetter } from "@/hooks/use-auth-ctx";
import { useInvalidatingMutation, type MutationCallbacks } from "@/hooks/use-invalidating-mutation";
import { makeRefetchInterval, makeStatusPoll, type RefetchIntervalFn } from "@/lib/query-poll";

import {
  cancelBacktest,
  createBacktest,
  createBacktestShare,
  deleteBacktest,
  getBacktest,
  getBacktestProgress,
  getStressTest,
  getTradeOhlcv,
  listBacktests,
  listBacktestTrades,
  listStressTests,
  postCostAssumption,
  postMonteCarlo,
  postParamStability,
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
  CreateCostAssumptionRequest,
  CreateMonteCarloRequest,
  CreateParamStabilityRequest,
  CreateWalkForwardRequest,
  ShareTokenResponse,
  StressTestCreatedResponse,
  StressTestDetail,
  StressTestListResponse,
  TradeItem,
  TradeListResponse,
  TradeOhlcvResponse,
} from "./schemas";

export { backtestKeys, stressTestKeys };

const POLL_INTERVAL_MS = 30_000;

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

function makeTradesFetcher(id: string, query: BacktestTradesQuery, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return listBacktestTrades(id, query, token);
  };
}

function makeTradeOhlcvFetcher(
  userId: string,
  backtestId: string,
  tradeIndex: number,
  getToken: TokenGetter,
) {
  return () => getTradeOhlcv(userId, backtestId, tradeIndex, getToken);
}

// 전체 trades 페이지 fetch — 리포트 파생 계산(분포/원장/마커)용 200-cap 해소.
// 상한 2000건 (BE 분포 집계 엔드포인트 도입 전 안전 cap — 초과 시 truncated 표기).
const ALL_TRADES_PAGE_SIZE = 200;
const MAX_ANALYTICS_TRADES = 2000;

export interface AllTradesResult {
  items: TradeItem[];
  total: number;
  /** cap 초과로 잘렸으면 true — 호출측 "표본 N건 기준" 캡션 의무 (Surface Trust). */
  truncated: boolean;
}

// first-page-then-parallel: 페이지 1 fetch 로 total 확보 → 잔여 offset 들을
// Promise.all 병렬 fetch (기존 순차 루프의 왕복 누적 latency 제거).
// export 는 단위 테스트용 (stressTestRefetchInterval export 패턴 mirror).
export function makeAllTradesFetcher(id: string, getToken: TokenGetter) {
  return async (): Promise<AllTradesResult> => {
    const token = await getToken();
    const first = await listBacktestTrades(id, { limit: ALL_TRADES_PAGE_SIZE, offset: 0 }, token);
    const total = first.total;

    // MAX_ANALYTICS_TRADES cap 유지 — 잔여 offset 은 min(total, cap) 까지만 생성.
    const cappedTotal = Math.min(total, MAX_ANALYTICS_TRADES);
    const restOffsets: number[] = [];
    for (let offset = ALL_TRADES_PAGE_SIZE; offset < cappedTotal; offset += ALL_TRADES_PAGE_SIZE) {
      restOffsets.push(offset);
    }
    const restPages = await Promise.all(
      restOffsets.map((offset) =>
        listBacktestTrades(id, { limit: ALL_TRADES_PAGE_SIZE, offset }, token),
      ),
    );

    // Promise.all 이 입력 순서를 보존 → offset 순 concat 보장.
    const items = [...first.items, ...restPages.flatMap((p) => p.items)];
    return { items, total, truncated: items.length < total };
  };
}

// --- polling interval — LESSON-004 guard ---------------------------------

const progressRefetchInterval = makeStatusPoll<BacktestProgressResponse>(
  (d) => d.status,
  new Set(["completed", "failed", "cancelled"]),
  POLL_INTERVAL_MS,
);

export type { MutationCallbacks };

// --- Hooks ---------------------------------------------------------------

export function useBacktests(
  query: BacktestListQuery,
): UseQueryResult<BacktestListResponse, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: backtestKeys.list(uid, query),
    queryFn: makeListFetcher(query, getToken),
  });
}

export function useBacktest(id: string | undefined): UseQueryResult<BacktestDetail, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: id ? backtestKeys.detail(uid, id) : backtestKeys.details(uid),
    queryFn: makeDetailFetcher(id ?? "", getToken),
    enabled: Boolean(id),
  });
}

export function useBacktestProgress(
  id: string | undefined,
): UseQueryResult<BacktestProgressResponse, Error> {
  const { uid, getToken } = useAuthCtx();
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
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: id ? backtestKeys.trades(uid, id, query) : backtestKeys.all(uid),
    queryFn: makeTradesFetcher(id ?? "", query, getToken),
    enabled: Boolean(id) && (options.enabled ?? true),
  });
}

export function useTradeOhlcv(
  backtestId: string | undefined,
  tradeIndex: number | undefined,
  options: { enabled?: boolean } = {},
): UseQueryResult<TradeOhlcvResponse, Error> {
  const { uid, getToken } = useAuthCtx();
  const isEnabled = Boolean(backtestId) && tradeIndex !== undefined && (options.enabled ?? true);
  return useQuery({
    queryKey:
      backtestId !== undefined && tradeIndex !== undefined
        ? backtestKeys.tradeOhlcv(uid, backtestId, tradeIndex)
        : backtestKeys.all(uid),
    queryFn: makeTradeOhlcvFetcher(uid, backtestId ?? "", tradeIndex ?? 0, getToken),
    enabled: isEnabled,
    staleTime: Infinity,
  });
}

export function useAllBacktestTrades(
  id: string | undefined,
  options: { enabled?: boolean } = {},
): UseQueryResult<AllTradesResult, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: id ? backtestKeys.tradesAll(uid, id) : backtestKeys.all(uid),
    queryFn: makeAllTradesFetcher(id ?? "", getToken),
    enabled: Boolean(id) && (options.enabled ?? true),
    // 완료 백테스트 trades 는 불변 — 재요청 불필요.
    staleTime: Infinity,
  });
}

export function useCreateBacktest(
  opts: MutationCallbacks<BacktestCreatedResponse> = {},
): UseMutationResult<BacktestCreatedResponse, Error, CreateBacktestRequest> {
  return useInvalidatingMutation(
    {
      mutationFn: (body: CreateBacktestRequest, token) => createBacktest(body, token),
      invalidateKeys: (uid) => [backtestKeys.lists(uid)],
    },
    opts,
  );
}

export function useCancelBacktest(
  opts: MutationCallbacks<BacktestCancelResponse> = {},
): UseMutationResult<BacktestCancelResponse, Error, string> {
  return useInvalidatingMutation(
    {
      mutationFn: (id: string, token) => cancelBacktest(id, token),
      invalidateKeys: (uid, res) => [
        backtestKeys.lists(uid),
        backtestKeys.detail(uid, res.backtest_id),
        backtestKeys.progress(uid, res.backtest_id),
      ],
    },
    opts,
  );
}

export function useDeleteBacktest(
  opts: MutationCallbacks<void> = {},
): UseMutationResult<void, Error, string> {
  return useInvalidatingMutation(
    {
      mutationFn: (id: string, token) => deleteBacktest(id, token),
      invalidateKeys: (uid) => [backtestKeys.lists(uid)],
      removeKeys: (uid, _void, id) => [
        backtestKeys.detail(uid, id),
        backtestKeys.progress(uid, id),
      ],
    },
    opts,
  );
}

// --- Sprint 41 Worker H — share link (LESSON-004/005/006 정합) -------------

export function useCreateBacktestShare(
  opts: MutationCallbacks<ShareTokenResponse> = {},
): UseMutationResult<ShareTokenResponse, Error, string> {
  const { getToken } = useAuthCtx();
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
  const { getToken } = useAuthCtx();
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
// 이력 표 1페이지. 페이지네이션 UI 는 없다 — 한 백테스트의 스트레스 실행이
// 20건을 넘는 사례가 아직 없어서, 넘기 전에는 열을 늘리는 것이 값을 낸다.
// ★넘으면 조용히 자르지 않고 표 아래에 「최근 20건만 표시(전체 N건)」을 고지한다.
// BE 상한은 `le=100` 이라 이 값을 올릴 여지는 남아 있다(`stress_test/router.py:106`).
const STRESS_TEST_HISTORY_LIMIT = 20;

// queryFn factory — 모듈 레벨 CallExpression 으로 @tanstack/query/exhaustive-deps 우회.
function makeStressTestFetcher(id: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return getStressTest(id, token);
  };
}

// [BL-414] 한 백테스트의 스트레스 테스트 이력 **1페이지**(최신 20건). 종전 fetcher 는
// limit=1 로 최신 1건만 가져왔고, 화면이 최신 1건만 보여준 뿌리가 그것이었다.
// ★「전체」가 아니다 — `offset` 은 0 고정이고 다음 페이지를 요청할 경로가 없다.
// 응답의 `total` 이 `items.length` 보다 크면 표가 그 사실을 화면에 고지한다
// (codex 적대 리뷰 P1, 2026-08-17 — 종전 주석이 「이력 전체」라 적어 코드보다 앞서 나갔다).
function makeStressTestHistoryFetcher(backtestId: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return listStressTests(backtestId, STRESS_TEST_HISTORY_LIMIT, token);
  };
}

// LESSON-004 guard: refetchInterval 은 module-level 순수 함수로, terminal status 에서 false 반환.
// React Query data 객체를 useEffect dep 로 쓰지 않아 CPU 100% 루프를 원천 차단.
export const stressTestRefetchInterval: RefetchIntervalFn<StressTestDetail> = makeStatusPoll(
  (d) => d.status,
  new Set(["completed", "failed"]),
  STRESS_TEST_POLL_MS,
);

// [BL-414] 이력 표 폴링 — 진행 중인 행이 하나라도 있을 때만. 도착 전(data 미도착)에는
// 지켜볼 행 자체가 없으므로 false 다 (상세 폴링과 여기가 다른 점).
export const stressTestHistoryRefetchInterval: RefetchIntervalFn<StressTestListResponse> =
  makeRefetchInterval((page) => {
    if (page == null) return false;
    const isPending = page.items.some(
      (item) => item.status === "queued" || item.status === "running",
    );
    return isPending ? STRESS_TEST_POLL_MS : false;
  });

export function useCreateMonteCarlo(
  opts: MutationCallbacks<StressTestCreatedResponse> = {},
): UseMutationResult<StressTestCreatedResponse, Error, CreateMonteCarloRequest> {
  return useInvalidatingMutation(
    {
      mutationFn: (body: CreateMonteCarloRequest, token) => postMonteCarlo(body, token),
      invalidateKeys: (uid) => [stressTestKeys.all(uid)],
    },
    opts,
  );
}

export function useCreateWalkForward(
  opts: MutationCallbacks<StressTestCreatedResponse> = {},
): UseMutationResult<StressTestCreatedResponse, Error, CreateWalkForwardRequest> {
  return useInvalidatingMutation(
    {
      mutationFn: (body: CreateWalkForwardRequest, token) => postWalkForward(body, token),
      invalidateKeys: (uid) => [stressTestKeys.all(uid)],
    },
    opts,
  );
}

// Sprint 50 — Cost Assumption Sensitivity (fees x slippage 9-cell grid).
export function useCreateCostAssumption(
  opts: MutationCallbacks<StressTestCreatedResponse> = {},
): UseMutationResult<StressTestCreatedResponse, Error, CreateCostAssumptionRequest> {
  return useInvalidatingMutation(
    {
      mutationFn: (body: CreateCostAssumptionRequest, token) => postCostAssumption(body, token),
      invalidateKeys: (uid) => [stressTestKeys.all(uid)],
    },
    opts,
  );
}

// Sprint 52 BL-223 — Param Stability (pine input_overrides 9-cell grid).
export function useCreateParamStability(
  opts: MutationCallbacks<StressTestCreatedResponse> = {},
): UseMutationResult<StressTestCreatedResponse, Error, CreateParamStabilityRequest> {
  return useInvalidatingMutation(
    {
      mutationFn: (body: CreateParamStabilityRequest, token) => postParamStability(body, token),
      invalidateKeys: (uid) => [stressTestKeys.all(uid)],
    },
    opts,
  );
}

export function useStressTest(id: string | null): UseQueryResult<StressTestDetail, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: id ? stressTestKeys.detail(uid, id) : stressTestKeys.all(uid),
    queryFn: makeStressTestFetcher(id ?? "", getToken),
    enabled: Boolean(id),
    refetchInterval: stressTestRefetchInterval,
    refetchIntervalInBackground: false,
  });
}

/**
 * [BL-414] 한 백테스트의 스트레스 테스트 이력 **첫 페이지**. 최신순(BE `created_at desc`)이라
 * `items[0]` 이 곧 최신 실행이다 — 별도의 "최신 1건" 질의를 두지 않는다.
 *
 * ★폴링 판정도 이 페이지 안의 행만 본다. 21번째 이후에 진행 중 행이 남아 있어도
 * 폴링은 안 돈다 — 그 창은 표의 잘림 고지로 사용자에게 드러난다.
 *
 * 진행 중인 행이 하나라도 있으면 폴링한다. 안 그러면 상세 패널은 "완료"를 그리는데
 * 같은 화면의 이력 행은 "대기"로 남아 한 화면이 두 가지를 말한다.
 */
export function useStressTestHistory(
  backtestId: string | undefined,
): UseQueryResult<StressTestListResponse, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: backtestId ? stressTestKeys.byBacktest(uid, backtestId) : stressTestKeys.all(uid),
    queryFn: makeStressTestHistoryFetcher(backtestId ?? "", getToken),
    enabled: Boolean(backtestId),
    refetchInterval: stressTestHistoryRefetchInterval,
    refetchIntervalInBackground: false,
  });
}
