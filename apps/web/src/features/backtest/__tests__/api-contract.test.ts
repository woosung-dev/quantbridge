// Backtest REST 래퍼의 경로·메서드·응답 스키마 계약을 고정한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

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
  listBacktestTrades,
  listBacktests,
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

const BACKTEST_ID = "00000000-0000-4000-a000-000000000001";
const STRATEGY_ID = "00000000-0000-4000-a000-000000000002";
const STRESS_TEST_ID = "00000000-0000-4000-a000-000000000003";
const CREATED_AT = "2026-08-24T00:00:00Z";
const PERIOD_START = "2026-01-01T00:00:00Z";
const PERIOD_END = "2026-02-01T00:00:00Z";

const BACKTEST_SUMMARY = {
  id: BACKTEST_ID,
  strategy_id: STRATEGY_ID,
  symbol: "BTC/USDT:USDT",
  timeframe: "1h",
  period_start: PERIOD_START,
  period_end: PERIOD_END,
  status: "completed",
  created_at: CREATED_AT,
  completed_at: CREATED_AT,
  metrics_summary: {
    total_return: "12.5",
    net_profit_abs: "1250",
    sharpe_ratio: "1.8",
    sharpe_convention: "daily",
    max_drawdown: "-4.2",
    num_trades: 8,
    total_open_trades: 0,
  },
};

const PARSED_BACKTEST_SUMMARY = {
  ...BACKTEST_SUMMARY,
  metrics_summary: {
    ...BACKTEST_SUMMARY.metrics_summary,
    total_return: 12.5,
    net_profit_abs: 1250,
    sharpe_ratio: 1.8,
    max_drawdown: -4.2,
  },
};

const BACKTEST_DETAIL = {
  ...BACKTEST_SUMMARY,
  initial_capital: "10000",
  config: {
    leverage: 2,
    fees: 0.00055,
    slippage: 0.00014,
    include_funding: true,
    fill_timing: "bar_close",
  },
  metrics: null,
  equity_curve: [{ timestamp: CREATED_AT, value: "10000" }],
  error: null,
  warnings: [],
};

const PARSED_BACKTEST_DETAIL = {
  ...PARSED_BACKTEST_SUMMARY,
  initial_capital: 10000,
  config: BACKTEST_DETAIL.config,
  metrics: null,
  equity_curve: [{ timestamp: CREATED_AT, value: 10000 }],
  error: null,
  warnings: [],
};

const TRADE = {
  trade_index: 7,
  direction: "long",
  status: "closed",
  entry_time: PERIOD_START,
  exit_time: PERIOD_END,
  entry_price: "100000",
  exit_price: "101000",
  size: "0.01",
  pnl: "10",
  return_pct: "1",
  fees: "0.11",
  runup_abs: "15",
  runup_pct: "1.5",
  drawdown_abs: "-2",
  drawdown_pct: "-0.2",
  bars_in_trade: 10,
  fee_paid: "0.05",
  slippage_paid: "0.06",
  cumulative_pnl: "10",
  exit_kind: "take_profit",
  comment: "Take profit",
};

const PARSED_TRADE = {
  ...TRADE,
  entry_price: 100000,
  exit_price: 101000,
  size: 0.01,
  pnl: 10,
  return_pct: 1,
  fees: 0.11,
  runup_abs: 15,
  runup_pct: 1.5,
  drawdown_abs: -2,
  drawdown_pct: -0.2,
  fee_paid: 0.05,
  slippage_paid: 0.06,
  cumulative_pnl: 10,
};

const TRADE_OHLCV = {
  backtest_id: BACKTEST_ID,
  trade_index: TRADE.trade_index,
  symbol: BACKTEST_SUMMARY.symbol,
  timeframe: BACKTEST_SUMMARY.timeframe,
  entry_time: TRADE.entry_time,
  exit_time: TRADE.exit_time,
  pad_bars: 3,
  stride: 1,
  truncated: false,
  bars: [
    {
      time: PERIOD_START,
      open: "100000",
      high: "101000",
      low: "99000",
      close: "100500",
      volume: "12.5",
    },
  ],
};

const PARSED_TRADE_OHLCV = {
  ...TRADE_OHLCV,
  bars: [
    {
      ...TRADE_OHLCV.bars[0],
      open: 100000,
      high: 101000,
      low: 99000,
      close: 100500,
      volume: 12.5,
    },
  ],
};

const CREATE_BACKTEST_REQUEST: CreateBacktestRequest = {
  strategy_id: STRATEGY_ID,
  symbol: BACKTEST_SUMMARY.symbol,
  timeframe: "1h",
  period_start: PERIOD_START,
  period_end: PERIOD_END,
  initial_capital: 10000,
  leverage: 2,
  fees_pct: 0.00055,
  slippage_pct: 0.00014,
  include_funding: true,
  allow_degraded_pine: true,
  fill_timing: "next_bar_open",
  default_qty_type: "strategy.percent_of_equity",
  default_qty_value: 25,
  trading_sessions: ["ny"],
};

const BACKTEST_CREATED = {
  backtest_id: BACKTEST_ID,
  status: "queued",
  created_at: CREATED_AT,
  replayed: true,
};

const STRESS_TEST_CREATED = {
  stress_test_id: STRESS_TEST_ID,
  kind: "monte_carlo",
  status: "queued",
  created_at: CREATED_AT,
};

const STRESS_TEST_DETAIL = {
  id: STRESS_TEST_ID,
  backtest_id: BACKTEST_ID,
  kind: "monte_carlo",
  status: "completed",
  params: { n_samples: 1000, seed: 42 },
  monte_carlo_result: null,
  walk_forward_result: null,
  cost_assumption_result: null,
  param_stability_result: null,
  error: null,
  created_at: CREATED_AT,
  started_at: CREATED_AT,
  completed_at: CREATED_AT,
};

const STRESS_TEST_SUMMARY = {
  id: STRESS_TEST_ID,
  backtest_id: BACKTEST_ID,
  kind: "monte_carlo",
  status: "completed",
  created_at: CREATED_AT,
  completed_at: CREATED_AT,
  headline_metric: { key: "max_drawdown_p95", value: "-4.2" },
};

const MONTE_CARLO_REQUEST: CreateMonteCarloRequest = {
  backtest_id: BACKTEST_ID,
  params: { n_samples: 100, seed: 7 },
};

const WALK_FORWARD_REQUEST: CreateWalkForwardRequest = {
  backtest_id: BACKTEST_ID,
  params: { train_bars: 100, test_bars: 20, step_bars: 10, max_folds: 5 },
};

const COST_ASSUMPTION_REQUEST: CreateCostAssumptionRequest = {
  backtest_id: BACKTEST_ID,
  params: { param_grid: { fees: ["0.0005"], slippage: ["0.0001"] } },
};

const PARAM_STABILITY_REQUEST: CreateParamStabilityRequest = {
  backtest_id: BACKTEST_ID,
  params: { param_grid: { fast_length: ["10"], slow_length: ["20"] } },
};

const CONVERT_INDICATOR_REQUEST: ConvertIndicatorRequest = {
  code: 'indicator("RSI")',
  strategy_name: "RSI strategy",
  mode: "sliced",
};

const CONVERT_INDICATOR_RESPONSE = {
  converted_code: 'strategy("RSI")',
  input_tokens: 100,
  output_tokens: 120,
  warnings: [],
  sliced_from: null,
  sliced_to: null,
  token_reduction_pct: null,
};

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("backtest API contract", () => {
  it("백테스트 목록은 GET 페이지 파라미터를 보내고 Decimal 요약값을 숫자로 파싱한다", async () => {
    const query = {
      limit: 20,
      offset: 40,
      order_by: "sharpe_ratio" as const,
      order: "asc" as const,
    };
    apiFetchMock.mockResolvedValueOnce({
      items: [BACKTEST_SUMMARY],
      total: 1,
      limit: 20,
      offset: 40,
    });

    await expect(listBacktests(query, "jwt")).resolves.toEqual({
      items: [PARSED_BACKTEST_SUMMARY],
      total: 1,
      limit: 20,
      offset: 40,
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/backtests", {
      method: "GET",
      token: "jwt",
      params: query,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("백테스트 상세는 식별자 GET 응답의 Decimal 필드를 숫자로 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce(BACKTEST_DETAIL);

    await expect(getBacktest(BACKTEST_ID, "jwt")).resolves.toEqual(PARSED_BACKTEST_DETAIL);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/backtests/${BACKTEST_ID}`, {
      method: "GET",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 동작: 백테스트 생성은 POST body를 검증하지만 BE의 replayed 필드는 응답에서 제외한다", async () => {
    apiFetchMock.mockResolvedValueOnce(BACKTEST_CREATED);

    await expect(createBacktest(CREATE_BACKTEST_REQUEST, "jwt")).resolves.toEqual({
      backtest_id: BACKTEST_ID,
      status: "queued",
      created_at: CREATED_AT,
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/backtests", {
      method: "POST",
      token: "jwt",
      body: CREATE_BACKTEST_REQUEST,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("백테스트 진행률은 progress GET 응답을 그대로 파싱한다", async () => {
    const progress = {
      backtest_id: BACKTEST_ID,
      status: "running",
      started_at: CREATED_AT,
      completed_at: null,
      error: null,
      stale: false,
    };
    apiFetchMock.mockResolvedValueOnce(progress);

    await expect(getBacktestProgress(BACKTEST_ID, "jwt")).resolves.toEqual(progress);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/backtests/${BACKTEST_ID}/progress`, {
      method: "GET",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("백테스트 거래 목록은 식별자 경로와 페이지 파라미터를 보내고 Decimal을 숫자로 파싱한다", async () => {
    const query = { limit: 50, offset: 100 };
    apiFetchMock.mockResolvedValueOnce({ items: [TRADE], total: 1, limit: 50, offset: 100 });

    await expect(listBacktestTrades(BACKTEST_ID, query, "jwt")).resolves.toEqual({
      items: [PARSED_TRADE],
      total: 1,
      limit: 50,
      offset: 100,
    });

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/backtests/${BACKTEST_ID}/trades`, {
      method: "GET",
      token: "jwt",
      params: query,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("거래 OHLCV는 거래 인덱스 경로와 token accessor 결과를 GET으로 보내고 Decimal을 숫자로 파싱한다", async () => {
    const getToken = vi.fn().mockResolvedValue("jwt");
    apiFetchMock.mockResolvedValueOnce(TRADE_OHLCV);

    await expect(
      getTradeOhlcv("user-id", BACKTEST_ID, TRADE.trade_index, getToken),
    ).resolves.toEqual(PARSED_TRADE_OHLCV);

    expect(getToken).toHaveBeenCalledOnce();
    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/backtests/${BACKTEST_ID}/trades/${TRADE.trade_index}/ohlcv`,
      { method: "GET", token: "jwt" },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("백테스트 취소는 cancel POST acknowledgement를 그대로 파싱한다", async () => {
    const acknowledgement = {
      backtest_id: BACKTEST_ID,
      status: "cancelling",
      message: "cancellation requested",
    };
    apiFetchMock.mockResolvedValueOnce(acknowledgement);

    await expect(cancelBacktest(BACKTEST_ID, "jwt")).resolves.toEqual(acknowledgement);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/backtests/${BACKTEST_ID}/cancel`, {
      method: "POST",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("백테스트 삭제는 식별자 DELETE와 인증만 보낸다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);

    await expect(deleteBacktest(BACKTEST_ID, "jwt")).resolves.toBeUndefined();

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/backtests/${BACKTEST_ID}`, {
      method: "DELETE",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("공유 링크 생성은 share POST 응답을 그대로 파싱한다", async () => {
    const share = {
      backtest_id: BACKTEST_ID,
      share_token: "share-token",
      share_url_path: "/share/backtests/share-token",
      revoked: false,
    };
    apiFetchMock.mockResolvedValueOnce(share);

    await expect(createBacktestShare(BACKTEST_ID, "jwt")).resolves.toEqual(share);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/backtests/${BACKTEST_ID}/share`, {
      method: "POST",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("공유 링크 폐기는 share DELETE와 인증만 보낸다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);

    await expect(revokeBacktestShare(BACKTEST_ID, "jwt")).resolves.toBeUndefined();

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/backtests/${BACKTEST_ID}/share`, {
      method: "DELETE",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("Monte Carlo 제출은 중첩 요청 body를 전용 POST 경로로 보내고 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce(STRESS_TEST_CREATED);

    await expect(postMonteCarlo(MONTE_CARLO_REQUEST, "jwt")).resolves.toEqual(STRESS_TEST_CREATED);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/stress-tests/monte-carlo", {
      method: "POST",
      token: "jwt",
      body: MONTE_CARLO_REQUEST,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("Walk-Forward 제출은 중첩 요청 body를 전용 POST 경로로 보내고 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ ...STRESS_TEST_CREATED, kind: "walk_forward" });

    await expect(postWalkForward(WALK_FORWARD_REQUEST, "jwt")).resolves.toEqual({
      ...STRESS_TEST_CREATED,
      kind: "walk_forward",
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/stress-tests/walk-forward", {
      method: "POST",
      token: "jwt",
      body: WALK_FORWARD_REQUEST,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("비용 가정 민감도 제출은 grid body를 전용 POST 경로로 보내고 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      ...STRESS_TEST_CREATED,
      kind: "cost_assumption_sensitivity",
    });

    await expect(postCostAssumption(COST_ASSUMPTION_REQUEST, "jwt")).resolves.toEqual({
      ...STRESS_TEST_CREATED,
      kind: "cost_assumption_sensitivity",
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/stress-tests/cost-assumption-sensitivity", {
      method: "POST",
      token: "jwt",
      body: COST_ASSUMPTION_REQUEST,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("파라미터 안정성 제출은 grid body를 전용 POST 경로로 보내고 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ ...STRESS_TEST_CREATED, kind: "param_stability" });

    await expect(postParamStability(PARAM_STABILITY_REQUEST, "jwt")).resolves.toEqual({
      ...STRESS_TEST_CREATED,
      kind: "param_stability",
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/stress-tests/param-stability", {
      method: "POST",
      token: "jwt",
      body: PARAM_STABILITY_REQUEST,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("스트레스 테스트 상세는 식별자 GET 응답을 그대로 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce(STRESS_TEST_DETAIL);

    await expect(getStressTest(STRESS_TEST_ID, "jwt")).resolves.toEqual(STRESS_TEST_DETAIL);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/stress-tests/${STRESS_TEST_ID}`, {
      method: "GET",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("스트레스 테스트 목록은 backtest 식별자와 페이지 파라미터를 GET으로 보낸다", async () => {
    const response = { items: [STRESS_TEST_SUMMARY], total: 1, limit: 20, offset: 0 };
    apiFetchMock.mockResolvedValueOnce(response);

    await expect(listStressTests(BACKTEST_ID, 20, "jwt")).resolves.toEqual(response);

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/stress-tests", {
      method: "GET",
      token: "jwt",
      params: { backtest_id: BACKTEST_ID, limit: 20, offset: 0 },
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("지표 변환은 strategy 경로로 body를 POST하고 변환 응답을 그대로 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce(CONVERT_INDICATOR_RESPONSE);

    await expect(convertIndicator(CONVERT_INDICATOR_REQUEST, "jwt")).resolves.toEqual(
      CONVERT_INDICATOR_RESPONSE,
    );

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/strategies/convert-indicator", {
      method: "POST",
      token: "jwt",
      body: CONVERT_INDICATOR_REQUEST,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });
});
