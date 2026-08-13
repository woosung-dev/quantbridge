// 완료된 백테스트 리포트 화면(`/backtests/[id]`) 을 검사하는 spec 들이 공유하는 mock.
//
// ★출처. 원래 `sprint32-dogfood-gate.spec.ts` 안에 있던 fixture 다. 그 파일이 들고 있던
// 고유 검증(차트 셸 · 범례 3항목 · MDD leverage 캡션 · 축 라벨)을 `sprint46-tier3-nth` 로
// 옮기면서, 다음 사람이 같은 mock 을 또 손으로 조립하지 않도록 여기로 승격했다.
//
// ★스키마 정합. equity_curve = `{timestamp,value}` · 벤치마크 = `metrics.buy_and_hold_curve`
// (`[ts, decimalString]` tuple) · id 는 `z.uuid()` variant `[89ab]` 준수. 이 셋 중 하나라도
// 어긋나면 화면이 조용히 미렌더된다(Surface Trust, ADR-019).

import type { Page } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./api-mock";

export const MOCK_BACKTEST_ID = "b7000000-0000-4000-8000-000000000001";
export const MOCK_STRATEGY_ID = "947bc980-0000-4000-a000-000000000001";

export const MOCK_BACKTEST_DETAIL = {
  id: MOCK_BACKTEST_ID,
  strategy_id: MOCK_STRATEGY_ID,
  symbol: "BTCUSDT",
  timeframe: "1h",
  period_start: "2024-01-01T00:00:00+00:00",
  period_end: "2024-03-01T00:00:00+00:00",
  status: "completed",
  created_at: "2026-05-01T00:00:00+00:00",
  completed_at: "2026-05-01T00:10:00+00:00",
  initial_capital: "10000",
  config: {
    leverage: 1,
    fees: 0.0006,
    slippage: 0.0005,
    include_funding: false,
  },
  metrics: {
    total_return: "0.1234",
    sharpe_ratio: "1.5",
    max_drawdown: "-0.345",
    win_rate: "0.55",
    num_trades: 42,
    mdd_unit: "equity_ratio",
    mdd_exceeds_capital: false,
    // 벤치마크(Buy & Hold) — ChartLegend BH 항목 노출용 (tuple [ts, decimalString]).
    buy_and_hold_curve: [
      ["2024-01-01T00:00:00+00:00", "10000"],
      ["2024-02-01T00:00:00+00:00", "10100"],
      ["2024-03-01T00:00:00+00:00", "10200"],
    ],
  },
  equity_curve: [
    { timestamp: "2024-01-01T00:00:00+00:00", value: "10000" },
    { timestamp: "2024-02-01T00:00:00+00:00", value: "10500" },
    { timestamp: "2024-03-01T00:00:00+00:00", value: "11234" },
  ],
  error: null,
};

/** 완료 백테스트 1건의 거래 목록 — 트레이드 마커 경로를 태우고 싶을 때 쓴다. */
export const MOCK_CLOSED_TRADE = {
  trade_index: 1,
  direction: "long",
  status: "closed",
  entry_time: "2024-01-15T14:32:00+00:00",
  exit_time: "2024-01-15T17:00:00+00:00",
  entry_price: "12345.67",
  exit_price: "12500.0",
  size: "0.05",
  pnl: "7.71",
  return_pct: "0.0125",
  fees: "0.5",
};

/**
 * `/backtests/[id]` 상세 + `/trades` + `/progress` 를 한 번에 mock 한다.
 *
 * `trades` 를 주면 거래 목록이 그 배열로 응답한다(기본 빈 배열). `/backtests/[id]` 는
 * 클라이언트 페치라 `page.route` mock 이 서버 prefetch 를 이긴다.
 */
export function routeBacktestDetail(
  page: Page,
  detail: typeof MOCK_BACKTEST_DETAIL,
  trades: Array<typeof MOCK_CLOSED_TRADE> = [],
) {
  return page.route(API_ROUTES.backtests, (route, request) => {
    const url = request.url();
    if (url.includes(`${MOCK_BACKTEST_ID}/trades`)) {
      return fulfillJson({
        items: trades,
        total: trades.length,
        limit: 200,
        offset: 0,
      })(route);
    }
    if (url.includes(`${MOCK_BACKTEST_ID}/progress`)) {
      // progress 는 별도 스키마 — 완료 상태만 알리면 detail.status 로 폴백된다.
      return fulfillJson({
        backtest_id: MOCK_BACKTEST_ID,
        status: "completed",
        started_at: "2026-05-01T00:05:00+00:00",
        completed_at: "2026-05-01T00:10:00+00:00",
        error: null,
        stale: false,
      })(route);
    }
    if (url.includes(MOCK_BACKTEST_ID)) {
      return fulfillJson(detail)(route);
    }
    return fulfillJson({ items: [], total: 0, limit: 20, offset: 0 })(route);
  });
}
