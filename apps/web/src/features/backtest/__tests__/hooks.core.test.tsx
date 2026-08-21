// 백테스트 핵심 React Query 훅 — API 경계·인증 토큰·disabled·polling 불변식 검증.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authMockState, resetAuthMock } from "@/lib/__mocks__/auth-client";

const apiFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import {
  backtestKeys,
  stressTestHistoryRefetchInterval,
  stressTestKeys,
  stressTestRefetchInterval,
  useBacktest,
  useBacktestProgress,
  useBacktestTrades,
  useAllBacktestTrades,
  useBacktests,
  useCancelBacktest,
  useCreateBacktest,
  useCreateBacktestShare,
  useCreateCostAssumption,
  useCreateMonteCarlo,
  useCreateParamStability,
  useCreateWalkForward,
  useDeleteBacktest,
  useRevokeBacktestShare,
  useStressTest,
  useStressTestHistory,
  useTradeOhlcv,
} from "../hooks";
import type {
  BacktestListResponse,
  CreateBacktestRequest,
  CreateCostAssumptionRequest,
  CreateMonteCarloRequest,
  CreateParamStabilityRequest,
  CreateWalkForwardRequest,
  ShareTokenResponse,
  TradeOhlcvResponse,
} from "../schemas";

const USER_ID = "user_core";
const BACKTEST_ID = "11111111-1111-4111-8111-111111111111";
const LIST_QUERY = { limit: 10, offset: 20 };
const TRADES_QUERY = { limit: 50, offset: 0 };
const STRESS_TEST_ID = "22222222-2222-4222-8222-222222222222";
const STRATEGY_ID = "33333333-3333-4333-8333-333333333333";
const STARTED_AT = "2026-08-01T00:00:00+00:00";
const COMPLETED_AT = "2026-08-02T00:00:00+00:00";

const LIST_RESPONSE: BacktestListResponse = {
  items: [],
  total: 0,
  limit: LIST_QUERY.limit,
  offset: LIST_QUERY.offset,
};

const OHLCV_RESPONSE: TradeOhlcvResponse = {
  backtest_id: BACKTEST_ID,
  trade_index: 7,
  symbol: "BTC/USDT",
  timeframe: "1h",
  entry_time: "2026-08-22T00:00:00+00:00",
  exit_time: null,
  pad_bars: 10,
  stride: 1,
  truncated: false,
  bars: [],
};

const SHARE_RESPONSE: ShareTokenResponse = {
  backtest_id: BACKTEST_ID,
  share_token: "share-token",
  share_url_path: `/backtests/${BACKTEST_ID}/share-token`,
  revoked: false,
};

const BACKTEST_DETAIL_RESPONSE = {
  id: BACKTEST_ID,
  strategy_id: STRATEGY_ID,
  symbol: "BTC/USDT",
  timeframe: "1h",
  period_start: STARTED_AT,
  period_end: COMPLETED_AT,
  status: "completed",
  created_at: STARTED_AT,
  completed_at: COMPLETED_AT,
  initial_capital: "10000",
};

const PROGRESS_RESPONSE = {
  backtest_id: BACKTEST_ID,
  status: "running",
  started_at: STARTED_AT,
  completed_at: null,
  error: null,
  stale: false,
};

const BACKTEST_CREATED_RESPONSE = {
  backtest_id: BACKTEST_ID,
  status: "queued",
  created_at: STARTED_AT,
};

const BACKTEST_CANCEL_RESPONSE = {
  backtest_id: BACKTEST_ID,
  status: "cancelling",
  message: "Cancellation requested",
};

const STRESS_TEST_CREATED_RESPONSE = {
  stress_test_id: STRESS_TEST_ID,
  kind: "monte_carlo",
  status: "queued",
  created_at: STARTED_AT,
};

const STRESS_TEST_DETAIL_RESPONSE = {
  id: STRESS_TEST_ID,
  backtest_id: BACKTEST_ID,
  kind: "monte_carlo",
  status: "completed",
  params: {},
  monte_carlo_result: null,
  walk_forward_result: null,
  cost_assumption_result: null,
  param_stability_result: null,
  error: null,
  created_at: STARTED_AT,
  started_at: STARTED_AT,
  completed_at: COMPLETED_AT,
};

const STRESS_TEST_HISTORY_RESPONSE = {
  items: [],
  total: 0,
  limit: 20,
  offset: 0,
};

const BACKTEST_REQUEST = {
  strategy_id: STRATEGY_ID,
  symbol: "BTC/USDT",
  timeframe: "1h",
  period_start: STARTED_AT,
  period_end: COMPLETED_AT,
  initial_capital: 10_000,
  leverage: 1,
  fees_pct: 0.001,
  slippage_pct: 0.0005,
  include_funding: true,
  fill_timing: "bar_close",
} satisfies CreateBacktestRequest;

const MONTE_CARLO_REQUEST = {
  backtest_id: BACKTEST_ID,
  params: { n_samples: 1000, seed: 42 },
} satisfies CreateMonteCarloRequest;

const WALK_FORWARD_REQUEST = {
  backtest_id: BACKTEST_ID,
  params: { train_bars: 120, test_bars: 30, step_bars: 30, max_folds: 4 },
} satisfies CreateWalkForwardRequest;

const COST_ASSUMPTION_REQUEST = {
  backtest_id: BACKTEST_ID,
  params: { param_grid: { fees: ["0.001"], slippage: ["0.0005"] } },
} satisfies CreateCostAssumptionRequest;

const PARAM_STABILITY_REQUEST = {
  backtest_id: BACKTEST_ID,
  params: { param_grid: { fast_length: ["10"], slow_length: ["20"] } },
} satisfies CreateParamStabilityRequest;

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function expectSingleApiFetch(
  path: string,
  options: {
    method: string;
    token: string | null;
    body?: unknown;
    params?: Record<string, string | number | boolean | undefined>;
  },
) {
  expect(apiFetchMock).toHaveBeenCalledTimes(1);
  expect(apiFetchMock).toHaveBeenCalledWith(path, options);
}

describe("backtest core hooks", () => {
  beforeEach(() => {
    resetAuthMock();
    authMockState.userId = USER_ID;
    apiFetchMock.mockReset();
  });

  it("useBacktests는 userId query key와 JWT를 list API에 전달한다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(LIST_RESPONSE);

    const { result } = renderHook(() => useBacktests(LIST_QUERY), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(LIST_RESPONSE));
    expect(queryClient.getQueryData(backtestKeys.list(USER_ID, LIST_QUERY))).toEqual(LIST_RESPONSE);
    expectSingleApiFetch("/api/v1/backtests", {
      method: "GET",
      token: "test-token",
      params: { limit: 10, offset: 20, order_by: undefined, order: undefined },
    });
  });

  it("useBacktest는 id가 없으면 API 요청을 시작하지 않는다", async () => {
    const queryClient = makeQueryClient();

    const { result } = renderHook(() => useBacktest(undefined), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.fetchStatus).toBe("idle"));
    expect(apiFetchMock).not.toHaveBeenCalled();
    expect(queryClient.getQueryData(backtestKeys.details(USER_ID))).toBeUndefined();
  });

  it("useBacktestProgress는 API 오류 뒤 polling을 중단한다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockRejectedValue(new Error("network down"));

    const { result } = renderHook(() => useBacktestProgress(BACKTEST_ID), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expectSingleApiFetch(`/api/v1/backtests/${BACKTEST_ID}/progress`, {
      method: "GET",
      token: "test-token",
    });

    const query = queryClient.getQueryCache().find({
      queryKey: backtestKeys.progress(USER_ID, BACKTEST_ID),
    });
    expect(query).toBeDefined();
    if (query === undefined) throw new Error("progress query가 생성되지 않았습니다");

    const refetchInterval = query.options.refetchInterval;
    expect(refetchInterval).toBeTypeOf("function");
    if (typeof refetchInterval === "function") {
      expect(refetchInterval(query)).toBe(false);
    }
  });

  it("useBacktestTrades는 명시적으로 disabled이면 API 요청을 시작하지 않는다", async () => {
    const queryClient = makeQueryClient();

    const { result } = renderHook(
      () => useBacktestTrades(BACKTEST_ID, TRADES_QUERY, { enabled: false }),
      { wrapper: makeWrapper(queryClient) },
    );

    await waitFor(() => expect(result.current.fetchStatus).toBe("idle"));
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("useTradeOhlcv는 getter 경계를 유지하고 결과를 무기한 stale로 둔다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(OHLCV_RESPONSE);

    const { result } = renderHook(() => useTradeOhlcv(BACKTEST_ID, 7), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(OHLCV_RESPONSE));
    const query = queryClient.getQueryCache().find({
      queryKey: backtestKeys.tradeOhlcv(USER_ID, BACKTEST_ID, 7),
    });
    expect(query?.options.staleTime).toBe(Infinity);
    expectSingleApiFetch(`/api/v1/backtests/${BACKTEST_ID}/trades/7/ohlcv`, {
      method: "GET",
      token: "test-token",
    });
  });

  it("useCreateBacktestShare는 성공 콜백 전에 JWT로 공유 API를 호출한다", async () => {
    const queryClient = makeQueryClient();
    const onSuccess = vi.fn();
    apiFetchMock.mockResolvedValue(SHARE_RESPONSE);

    const { result } = renderHook(() => useCreateBacktestShare({ onSuccess }), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(BACKTEST_ID)).resolves.toEqual(SHARE_RESPONSE);
    expect(onSuccess).toHaveBeenCalledWith(SHARE_RESPONSE);
    expectSingleApiFetch(`/api/v1/backtests/${BACKTEST_ID}/share`, {
      method: "POST",
      token: "test-token",
    });
  });

  it("useBacktest는 상세 GET 응답을 스키마 변환 뒤 한 번만 반환한다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(BACKTEST_DETAIL_RESPONSE);

    const { result } = renderHook(() => useBacktest(BACKTEST_ID), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data?.initial_capital).toBe(10_000));
    expect(result.current.data).toMatchObject({ id: BACKTEST_ID, symbol: "BTC/USDT" });
    expectSingleApiFetch(`/api/v1/backtests/${BACKTEST_ID}`, {
      method: "GET",
      token: "test-token",
    });
  });

  it("useBacktestProgress는 진행 응답을 그대로 반환한다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(PROGRESS_RESPONSE);

    const { result } = renderHook(() => useBacktestProgress(BACKTEST_ID), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(PROGRESS_RESPONSE));
    expect(result.current.data?.stale).toBe(false);
    expectSingleApiFetch(`/api/v1/backtests/${BACKTEST_ID}/progress`, {
      method: "GET",
      token: "test-token",
    });
  });

  it("useBacktestTrades는 pagination params를 포함한 거래 목록을 한 번 요청한다", async () => {
    const queryClient = makeQueryClient();
    const response = { items: [], total: 0, limit: 50, offset: 0 };
    apiFetchMock.mockResolvedValue(response);

    const { result } = renderHook(() => useBacktestTrades(BACKTEST_ID, TRADES_QUERY), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(response));
    expect(result.current.data?.total).toBe(0);
    expectSingleApiFetch(`/api/v1/backtests/${BACKTEST_ID}/trades`, {
      method: "GET",
      token: "test-token",
      params: { limit: 50, offset: 0 },
    });
  });

  it("useAllBacktestTrades는 첫 페이지 결과를 analytics 형태로 반환한다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue({ items: [], total: 0, limit: 200, offset: 0 });

    const { result } = renderHook(() => useAllBacktestTrades(BACKTEST_ID), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() =>
      expect(result.current.data).toEqual({ items: [], total: 0, truncated: false }),
    );
    expect(result.current.data?.truncated).toBe(false);
    expectSingleApiFetch(`/api/v1/backtests/${BACKTEST_ID}/trades`, {
      method: "GET",
      token: "test-token",
      params: { limit: 200, offset: 0 },
    });
  });

  it("useCreateBacktest는 검증된 body와 JWT로 생성 요청을 한 번 보낸다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(BACKTEST_CREATED_RESPONSE);

    const { result } = renderHook(() => useCreateBacktest(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(BACKTEST_REQUEST)).resolves.toEqual(
      BACKTEST_CREATED_RESPONSE,
    );
    expectSingleApiFetch("/api/v1/backtests", {
      method: "POST",
      token: "test-token",
      body: BACKTEST_REQUEST,
    });
  });

  it("useCancelBacktest는 cancel 경로의 응답을 한 번 반환한다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(BACKTEST_CANCEL_RESPONSE);

    const { result } = renderHook(() => useCancelBacktest(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(BACKTEST_ID)).resolves.toEqual(
      BACKTEST_CANCEL_RESPONSE,
    );
    expectSingleApiFetch(`/api/v1/backtests/${BACKTEST_ID}/cancel`, {
      method: "POST",
      token: "test-token",
    });
  });

  it("useDeleteBacktest는 204 결과를 보존하고 DELETE를 한 번 보낸다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteBacktest(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(BACKTEST_ID)).resolves.toBeUndefined();
    expect(result.current.data).toBeUndefined();
    expectSingleApiFetch(`/api/v1/backtests/${BACKTEST_ID}`, {
      method: "DELETE",
      token: "test-token",
    });
  });

  it("useRevokeBacktestShare는 204 결과를 보존하고 공유 revoke를 한 번 보낸다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(undefined);

    const { result } = renderHook(() => useRevokeBacktestShare(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(BACKTEST_ID)).resolves.toBeUndefined();
    expect(result.current.data).toBeUndefined();
    expectSingleApiFetch(`/api/v1/backtests/${BACKTEST_ID}/share`, {
      method: "DELETE",
      token: "test-token",
    });
  });

  it("useCreateMonteCarlo는 Monte Carlo body를 한 번 전송한다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(STRESS_TEST_CREATED_RESPONSE);

    const { result } = renderHook(() => useCreateMonteCarlo(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(MONTE_CARLO_REQUEST)).resolves.toEqual(
      STRESS_TEST_CREATED_RESPONSE,
    );
    expectSingleApiFetch("/api/v1/stress-tests/monte-carlo", {
      method: "POST",
      token: "test-token",
      body: MONTE_CARLO_REQUEST,
    });
  });

  it("useCreateWalkForward는 Walk-Forward body를 한 번 전송한다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(STRESS_TEST_CREATED_RESPONSE);

    const { result } = renderHook(() => useCreateWalkForward(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(WALK_FORWARD_REQUEST)).resolves.toEqual(
      STRESS_TEST_CREATED_RESPONSE,
    );
    expectSingleApiFetch("/api/v1/stress-tests/walk-forward", {
      method: "POST",
      token: "test-token",
      body: WALK_FORWARD_REQUEST,
    });
  });

  it("useCreateCostAssumption은 비용 민감도 body를 한 번 전송한다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(STRESS_TEST_CREATED_RESPONSE);

    const { result } = renderHook(() => useCreateCostAssumption(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(COST_ASSUMPTION_REQUEST)).resolves.toEqual(
      STRESS_TEST_CREATED_RESPONSE,
    );
    expectSingleApiFetch("/api/v1/stress-tests/cost-assumption-sensitivity", {
      method: "POST",
      token: "test-token",
      body: COST_ASSUMPTION_REQUEST,
    });
  });

  it("useCreateParamStability는 파라미터 안정성 body를 한 번 전송한다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(STRESS_TEST_CREATED_RESPONSE);

    const { result } = renderHook(() => useCreateParamStability(), {
      wrapper: makeWrapper(queryClient),
    });

    await expect(result.current.mutateAsync(PARAM_STABILITY_REQUEST)).resolves.toEqual(
      STRESS_TEST_CREATED_RESPONSE,
    );
    expectSingleApiFetch("/api/v1/stress-tests/param-stability", {
      method: "POST",
      token: "test-token",
      body: PARAM_STABILITY_REQUEST,
    });
  });

  it("useStressTest는 terminal 상세 결과를 한 번 반환하고 polling을 멈춘다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(STRESS_TEST_DETAIL_RESPONSE);

    const { result } = renderHook(() => useStressTest(STRESS_TEST_ID), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(STRESS_TEST_DETAIL_RESPONSE));
    const query = queryClient.getQueryCache().find({
      queryKey: stressTestKeys.detail(USER_ID, STRESS_TEST_ID),
    });
    expect(query?.options.refetchInterval).toBeTypeOf("function");
    expectSingleApiFetch(`/api/v1/stress-tests/${STRESS_TEST_ID}`, {
      method: "GET",
      token: "test-token",
    });
  });

  it("useStressTestHistory는 backtest_id와 limit=20으로 첫 페이지를 한 번 요청한다", async () => {
    const queryClient = makeQueryClient();
    apiFetchMock.mockResolvedValue(STRESS_TEST_HISTORY_RESPONSE);

    const { result } = renderHook(() => useStressTestHistory(BACKTEST_ID), {
      wrapper: makeWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.data).toEqual(STRESS_TEST_HISTORY_RESPONSE));
    expect(queryClient.getQueryData(stressTestKeys.byBacktest(USER_ID, BACKTEST_ID))).toEqual(
      STRESS_TEST_HISTORY_RESPONSE,
    );
    expectSingleApiFetch("/api/v1/stress-tests", {
      method: "GET",
      token: "test-token",
      params: { backtest_id: BACKTEST_ID, limit: 20, offset: 0 },
    });
  });

  it("stressTestRefetchInterval은 오류 query에서 false를 반환한다", () => {
    const query = {
      state: { status: "error", data: undefined },
    } as Parameters<typeof stressTestRefetchInterval>[0];

    expect(stressTestRefetchInterval(query)).toBe(false);
  });

  it("stressTestHistoryRefetchInterval은 terminal 이력에서 false를 반환한다", () => {
    const query = {
      state: { status: "success", data: STRESS_TEST_HISTORY_RESPONSE },
    } as Parameters<typeof stressTestHistoryRefetchInterval>[0];

    expect(stressTestHistoryRefetchInterval(query)).toBe(false);
  });
});
