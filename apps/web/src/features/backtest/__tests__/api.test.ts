// 백테스트 REST wrapper가 apiFetch에 전달하는 경로·요청 형태와 응답 스키마 경계를 검증한다.

import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({
  apiFetch: apiFetchMock,
}));

import {
  cancelBacktest,
  createBacktest,
  getBacktestProgress,
  getTradeOhlcv,
  listBacktests,
  postMonteCarlo,
} from "../api";
import type { CreateBacktestRequest, CreateMonteCarloRequest } from "../schemas";

const BACKTEST_ID = "11111111-1111-4111-8111-111111111111";
const STRATEGY_ID = "22222222-2222-4222-8222-222222222222";
const CREATED_AT = "2026-08-22T00:00:00+00:00";
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

afterEach(() => {
  apiFetchMock.mockReset();
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
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/backtests/${BACKTEST_ID}/progress`, {
      method: "GET",
      token: TOKEN,
    });
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
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/backtests/${BACKTEST_ID}/trades/3/ohlcv`, {
      method: "GET",
      token: TOKEN,
    });
  });

  it("cancelBacktest는 취소 경로로 POST하고 상태 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      backtest_id: BACKTEST_ID,
      status: "cancelling",
      message: "Cancellation requested",
    });

    const result = await cancelBacktest(BACKTEST_ID, TOKEN);

    expect(result.status).toBe("cancelling");
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/backtests/${BACKTEST_ID}/cancel`, {
      method: "POST",
      token: TOKEN,
    });
  });

  it("postMonteCarlo는 stress-tests 경로에 중첩 파라미터를 POST한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      stress_test_id: "33333333-3333-4333-8333-333333333333",
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
  });
});
