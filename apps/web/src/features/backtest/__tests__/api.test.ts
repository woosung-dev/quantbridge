// 백테스트 REST wrapper가 apiFetch에 전달하는 경로·요청 형태와 응답 스키마 경계를 검증한다.

import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiFetchMock };
});

import { ApiError } from "@/lib/api-client";
import {
  cancelBacktest,
  convertIndicator,
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
} from "../api";
import type {
  ConvertIndicatorRequest,
  CreateBacktestRequest,
  CreateCostAssumptionRequest,
  CreateMonteCarloRequest,
  CreateParamStabilityRequest,
  CreateWalkForwardRequest,
} from "../schemas";

const BACKTEST_ID = "11111111-1111-4111-8111-111111111111";
const STRATEGY_ID = "22222222-2222-4222-8222-222222222222";
const STRESS_TEST_ID = "33333333-3333-4333-8333-333333333333";
const CREATED_AT = "2026-08-22T00:00:00+00:00";
const PERIOD_END = "2026-08-22T01:00:00+00:00";
const TOKEN = "test-token";

const createBacktestBody: CreateBacktestRequest = {
  strategy_id: STRATEGY_ID,
  symbol: "BTCUSDT",
  timeframe: "1h",
  period_start: "2026-01-01T00:00:00+00:00",
  period_end: "2026-02-01T00:00:00+00:00",
  initial_capital: 10_000,
  leverage: 1,
  fees_pct: 0.001,
  slippage_pct: 0.0005,
  include_funding: true,
  fill_timing: "bar_close",
};

const monteCarloBody: CreateMonteCarloRequest = {
  backtest_id: BACKTEST_ID,
  params: { n_samples: 100, seed: 42 },
};

const walkForwardBody: CreateWalkForwardRequest = {
  backtest_id: BACKTEST_ID,
  params: { train_bars: 100, test_bars: 25, step_bars: 25, max_folds: 3 },
};

const costAssumptionBody: CreateCostAssumptionRequest = {
  backtest_id: BACKTEST_ID,
  params: { param_grid: { fees: ["0.001", "0.002"], slippage: ["0.0005", "0.001"] } },
};

const paramStabilityBody: CreateParamStabilityRequest = {
  backtest_id: BACKTEST_ID,
  params: { param_grid: { fast_length: ["10", "20"], slow_length: ["30", "50"] } },
};

const convertIndicatorBody: ConvertIndicatorRequest = {
  code: "indicator('Example')",
  strategy_name: "Example Strategy",
  mode: "sliced",
};

afterEach(() => {
  apiFetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("backtest api", () => {
  it("listBacktests는 정렬·페이지 쿼리를 backtests GET으로 전달하고 목록을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0, limit: 20, offset: 40 });

    const result = await listBacktests(
      { limit: 20, offset: 40, order_by: "sharpe_ratio", order: "desc" },
      TOKEN,
    );

    expect(result).toEqual({ items: [], total: 0, limit: 20, offset: 40 });
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/backtests", {
      method: "GET",
      token: TOKEN,
      params: { limit: 20, offset: 40, order_by: "sharpe_ratio", order: "desc" },
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("getBacktest는 식별자 GET 결과를 상세 스키마로 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      id: BACKTEST_ID,
      strategy_id: STRATEGY_ID,
      symbol: "BTCUSDT",
      timeframe: "1h",
      period_start: CREATED_AT,
      period_end: PERIOD_END,
      status: "completed",
      created_at: CREATED_AT,
      completed_at: PERIOD_END,
      initial_capital: "10000",
    });

    const result = await getBacktest(BACKTEST_ID, TOKEN);

    expect(result).toMatchObject({ id: BACKTEST_ID, initial_capital: 10_000 });
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/backtests/11111111-1111-4111-8111-111111111111",
      {
        method: "GET",
        token: TOKEN,
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("createBacktest는 검증한 본문을 backtests POST로 전달하고 생성 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      backtest_id: BACKTEST_ID,
      status: "queued",
      created_at: CREATED_AT,
    });

    const result = await createBacktest(createBacktestBody, TOKEN);

    expect(result).toMatchObject({ backtest_id: BACKTEST_ID, status: "queued" });
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/backtests", {
      method: "POST",
      token: TOKEN,
      body: createBacktestBody,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("getBacktestProgress는 누락된 stale을 false로 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      backtest_id: BACKTEST_ID,
      status: "running",
      started_at: CREATED_AT,
      completed_at: null,
      error: null,
    });

    const result = await getBacktestProgress(BACKTEST_ID, TOKEN);

    expect(result.stale).toBe(false);
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/backtests/11111111-1111-4111-8111-111111111111/progress",
      {
        method: "GET",
        token: TOKEN,
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("listBacktestTrades는 페이지 쿼리를 trades GET으로 전달하고 Decimal을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      items: [
        {
          trade_index: 7,
          direction: "long",
          status: "closed",
          entry_time: CREATED_AT,
          exit_time: PERIOD_END,
          entry_price: "100",
          exit_price: "112.5",
          size: "2",
          pnl: "25",
          return_pct: "12.5",
          fees: "0.2",
        },
      ],
      total: 1,
      limit: 50,
      offset: 100,
    });

    const result = await listBacktestTrades(BACKTEST_ID, { limit: 50, offset: 100 }, TOKEN);

    expect(result.items[0]).toMatchObject({ trade_index: 7, pnl: 25 });
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/backtests/11111111-1111-4111-8111-111111111111/trades",
      {
        method: "GET",
        token: TOKEN,
        params: { limit: 50, offset: 100 },
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("getTradeOhlcv는 userId 대신 await한 getToken 값으로 OHLCV GET을 호출한다", async () => {
    const getToken = vi.fn(async () => TOKEN);
    apiFetchMock.mockResolvedValueOnce({
      backtest_id: BACKTEST_ID,
      trade_index: 3,
      symbol: "BTCUSDT",
      timeframe: "1h",
      entry_time: CREATED_AT,
      exit_time: null,
      pad_bars: 10,
      stride: 1,
      truncated: false,
      bars: [
        {
          time: CREATED_AT,
          open: "100",
          high: "102",
          low: "99",
          close: "101",
          volume: "12",
        },
      ],
    });

    const result = await getTradeOhlcv("unused-user-id", BACKTEST_ID, 3, getToken);

    expect(getToken).toHaveBeenCalledOnce();
    expect(result.bars[0]?.close).toBe(101);
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/backtests/11111111-1111-4111-8111-111111111111/trades/3/ohlcv",
      {
        method: "GET",
        token: TOKEN,
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("cancelBacktest는 취소 경로로 POST하고 상태 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      backtest_id: BACKTEST_ID,
      status: "cancelling",
      message: "Cancellation requested",
    });

    const result = await cancelBacktest(BACKTEST_ID, TOKEN);

    expect(result.status).toBe("cancelling");
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/backtests/11111111-1111-4111-8111-111111111111/cancel",
      {
        method: "POST",
        token: TOKEN,
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("deleteBacktest는 대상 backtest를 DELETE하고 undefined를 반환한다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);

    const result = await deleteBacktest(BACKTEST_ID, TOKEN);

    expect(result).toBeUndefined();
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/backtests/11111111-1111-4111-8111-111111111111",
      {
        method: "DELETE",
        token: TOKEN,
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("createBacktestShare는 share POST 결과를 토큰 응답으로 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      backtest_id: BACKTEST_ID,
      share_token: "public-token",
      share_url_path: "/shared/public-token",
      revoked: false,
    });

    const result = await createBacktestShare(BACKTEST_ID, TOKEN);

    expect(result).toMatchObject({ share_token: "public-token", revoked: false });
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/backtests/11111111-1111-4111-8111-111111111111/share",
      {
        method: "POST",
        token: TOKEN,
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("revokeBacktestShare는 share DELETE를 한 번 호출하고 undefined를 반환한다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);

    const result = await revokeBacktestShare(BACKTEST_ID, TOKEN);

    expect(result).toBeUndefined();
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/backtests/11111111-1111-4111-8111-111111111111/share",
      {
        method: "DELETE",
        token: TOKEN,
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("postMonteCarlo는 stress-tests 경로에 중첩 파라미터를 POST한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      stress_test_id: STRESS_TEST_ID,
      kind: "monte_carlo",
      status: "queued",
      created_at: CREATED_AT,
    });

    const result = await postMonteCarlo(monteCarloBody, TOKEN);

    expect(result.kind).toBe("monte_carlo");
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/stress-tests/monte-carlo", {
      method: "POST",
      token: TOKEN,
      body: monteCarloBody,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("postWalkForward는 walk-forward POST 본문과 queued 응답을 전달한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      stress_test_id: STRESS_TEST_ID,
      kind: "walk_forward",
      status: "queued",
      created_at: CREATED_AT,
    });

    const result = await postWalkForward(walkForwardBody, TOKEN);

    expect(result).toMatchObject({ stress_test_id: STRESS_TEST_ID, kind: "walk_forward" });
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/stress-tests/walk-forward", {
      method: "POST",
      token: TOKEN,
      body: walkForwardBody,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("postCostAssumption은 비용 격자 본문을 sensitivity 경로로 POST한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      stress_test_id: STRESS_TEST_ID,
      kind: "cost_assumption_sensitivity",
      status: "queued",
      created_at: CREATED_AT,
    });

    const result = await postCostAssumption(costAssumptionBody, TOKEN);

    expect(result.kind).toBe("cost_assumption_sensitivity");
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/stress-tests/cost-assumption-sensitivity", {
      method: "POST",
      token: TOKEN,
      body: costAssumptionBody,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("postParamStability는 Pine 입력 격자 본문을 stability 경로로 POST한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      stress_test_id: STRESS_TEST_ID,
      kind: "param_stability",
      status: "queued",
      created_at: CREATED_AT,
    });

    const result = await postParamStability(paramStabilityBody, TOKEN);

    expect(result.kind).toBe("param_stability");
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/stress-tests/param-stability", {
      method: "POST",
      token: TOKEN,
      body: paramStabilityBody,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("getStressTest는 상세 GET 결과를 스트레스 테스트 스키마로 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      id: STRESS_TEST_ID,
      backtest_id: BACKTEST_ID,
      kind: "monte_carlo",
      status: "completed",
      params: { n_samples: 100 },
      created_at: CREATED_AT,
      completed_at: PERIOD_END,
    });

    const result = await getStressTest(STRESS_TEST_ID, TOKEN);

    expect(result).toMatchObject({ id: STRESS_TEST_ID, params: { n_samples: 100 } });
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/stress-tests/33333333-3333-4333-8333-333333333333",
      {
        method: "GET",
        token: TOKEN,
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("listStressTests는 backtest_id와 고정 offset을 목록 GET params로 전달한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      items: [
        {
          id: STRESS_TEST_ID,
          backtest_id: BACKTEST_ID,
          kind: "monte_carlo",
          status: "completed",
          created_at: CREATED_AT,
          completed_at: PERIOD_END,
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    });

    const result = await listStressTests(BACKTEST_ID, 10, TOKEN);

    expect(result.items[0]?.headline_metric).toBeNull();
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/stress-tests", {
      method: "GET",
      token: TOKEN,
      params: { backtest_id: BACKTEST_ID, limit: 10, offset: 0 },
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("convertIndicator는 전략 변환 전용 경로로 POST하고 기본 warnings를 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      converted_code: "strategy('Example')",
      input_tokens: 10,
      output_tokens: 12,
      sliced_from: null,
      sliced_to: null,
      token_reduction_pct: null,
    });

    const result = await convertIndicator(convertIndicatorBody, TOKEN);

    expect(result).toMatchObject({ converted_code: "strategy('Example')", warnings: [] });
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies/convert-indicator", {
      method: "POST",
      token: TOKEN,
      body: convertIndicatorBody,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("apiFetch의 ApiError를 status·code를 보존한 같은 객체로 전파한다", async () => {
    const error = new ApiError(429, "rate_limited", "API 429 /api/v1/backtests", {
      detail: { code: "rate_limited" },
    });
    apiFetchMock.mockRejectedValueOnce(error);

    await expect(listBacktests({ limit: 20, offset: 0 }, TOKEN)).rejects.toBe(error);
    expect(error.status).toBe(429);
    expect(error.code).toBe("rate_limited");
  });

  it("getTradeOhlcv도 getToken 호출 뒤 ApiError를 감싸지 않고 전파한다", async () => {
    const error = new ApiError(503, "upstream_unavailable", "API 503 /ohlcv");
    const getToken = vi.fn(async () => TOKEN);
    apiFetchMock.mockRejectedValueOnce(error);

    await expect(getTradeOhlcv("unused-user-id", BACKTEST_ID, 0, getToken)).rejects.toBe(error);
    expect(getToken).toHaveBeenCalledOnce();
    expect(error.status).toBe(503);
    expect(error.code).toBe("upstream_unavailable");
  });

  it("listBacktests는 pagination 계약이 깨진 응답을 조용히 통과시키지 않는다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0, limit: 0 });

    await expect(listBacktests({ limit: 0, offset: 0 }, TOKEN)).rejects.toThrow();
  });

  it("getTradeOhlcv는 non-finite Decimal 응답을 파싱 오류로 막는다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      backtest_id: BACKTEST_ID,
      trade_index: 0,
      symbol: "BTCUSDT",
      timeframe: "1h",
      entry_time: CREATED_AT,
      exit_time: null,
      pad_bars: 0,
      stride: 1,
      truncated: false,
      bars: [
        {
          time: CREATED_AT,
          open: "100",
          high: "102",
          low: "99",
          close: "NaN",
          volume: "12",
        },
      ],
    });

    await expect(
      getTradeOhlcv("unused-user-id", BACKTEST_ID, 0, async () => TOKEN),
    ).rejects.toThrow("non-finite decimal string");
  });

  it("postMonteCarlo는 enum 계약을 벗어난 생성 응답을 파싱 오류로 막는다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      stress_test_id: STRESS_TEST_ID,
      kind: "not-a-stress-test",
      status: "queued",
      created_at: CREATED_AT,
    });

    await expect(postMonteCarlo(monteCarloBody, TOKEN)).rejects.toThrow();
  });

  it("createBacktest는 initial_capital=0 요청을 HTTP 호출 전에 거부한다", async () => {
    await expect(
      createBacktest({ ...createBacktestBody, initial_capital: 0 }, TOKEN),
    ).rejects.toThrow();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("createBacktest는 음수 fees_pct 요청을 HTTP 호출 전에 거부한다", async () => {
    await expect(
      createBacktest({ ...createBacktestBody, fees_pct: -0.001 }, TOKEN),
    ).rejects.toThrow();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("listBacktests는 선택 정렬값이 없으면 undefined를 apiFetch에 그대로 전달한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0, limit: 0, offset: 0 });

    await listBacktests({ limit: 0, offset: 0 }, null);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/backtests", {
      method: "GET",
      token: null,
      params: { limit: 0, offset: 0, order_by: undefined, order: undefined },
    });
  });

  it("listBacktests는 0 limit과 음수 offset을 변형 없이 전달한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0, limit: 0, offset: -1 });

    const result = await listBacktests({ limit: 0, offset: -1 }, TOKEN);

    expect(result).toEqual({ items: [], total: 0, limit: 0, offset: -1 });
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/backtests", {
      method: "GET",
      token: TOKEN,
      params: { limit: 0, offset: -1, order_by: undefined, order: undefined },
    });
  });

  it("listBacktestTrades는 빈 목록의 0 limit과 음수 offset을 변형 없이 전달한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0, limit: 0, offset: -1 });

    const result = await listBacktestTrades(BACKTEST_ID, { limit: 0, offset: -1 }, TOKEN);

    expect(result).toEqual({ items: [], total: 0, limit: 0, offset: -1 });
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/v1/backtests/11111111-1111-4111-8111-111111111111/trades",
      {
        method: "GET",
        token: TOKEN,
        params: { limit: 0, offset: -1 },
      },
    );
  });

  it.each([0, -1])("getTradeOhlcv는 tradeIndex=%i를 경로에 그대로 쓴다", async (tradeIndex) => {
    apiFetchMock.mockResolvedValueOnce({
      backtest_id: BACKTEST_ID,
      trade_index: tradeIndex,
      symbol: "BTCUSDT",
      timeframe: "1h",
      entry_time: CREATED_AT,
      exit_time: null,
      pad_bars: 0,
      stride: 1,
      truncated: false,
      bars: [],
    });

    const result = await getTradeOhlcv(
      "unused-user-id",
      BACKTEST_ID,
      tradeIndex,
      async () => TOKEN,
    );

    expect(result).toMatchObject({ trade_index: tradeIndex, bars: [] });
    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/backtests/${BACKTEST_ID}/trades/${tradeIndex}/ohlcv`,
      {
        method: "GET",
        token: TOKEN,
      },
    );
  });

  it("apiFetch는 undefined 쿼리를 생략하고 204 응답을 void로 반환한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch: actualApiFetch } =
      await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");

    const result = await actualApiFetch<void>("/api/v1/backtests", {
      method: "DELETE",
      params: { limit: 0, offset: -1, order_by: undefined },
    });

    expect(result).toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const call = fetchMock.mock.calls[0];
    expect(call).toBeDefined();
    if (!call) throw new Error("fetch must be called");
    const [url] = call;
    expect(String(url)).toContain("limit=0");
    expect(String(url)).toContain("offset=-1");
    expect(String(url)).not.toContain("order_by=undefined");
  });
});
