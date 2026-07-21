import { expect, test, type Page } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./fixtures/api-mock";

// Sprint 32 — Surface Trust Recovery dogfood gate.
//
// codex G.0 P1-2 surgery: BL-157 live-smoke 가 public pages only / backend down 전제 /
// 4xx-5xx 무시 / unexpected error <5 허용 → chart/form/result PR dogfood 회귀 검출 불가.
// 본 gate 는 authed `/backtests/new` → run → result render → chart interaction 까지
// 통합 시나리오 검증.
//
// 검증 영역 (C 이식 후 등가 재작성 — 5탭 IA → 번호 섹션 단일 스크롤 BacktestReportShell):
//   §1 chart shell — equity-chart-v2 / equity-pane-wrapper / drawdown-pane-wrapper /
//      ChartLegend(role=list "차트 범례") 3항목 (BL-169+170)
//   §2 MDD caption — KeyStatsStrip "최대 낙폭" 카드 foot 의 leverage/자본초과 캡션 (BL-156,
//      buildMddCaption — 이전 mdd-leverage-caption testid 는 KPI foot 로 흡수됨)
//   §3 error UX — 422 friendly_message + unsupported_builtins (BL-163)
//   §4 axis labels + markers — AxisLabelBar (BL-171+172)
//
// C 이식 스키마 정합: equity_curve = {timestamp,value}, 벤치마크 = metrics.buy_and_hold_curve
// ([ts, decimalString] tuple), 전략/백테스트 id 는 z.uuid() variant [89ab] 준수.
//
// 의존: chromium-authed project + storageState. /backtests/[id] · /backtests/new 는
// 클라이언트 페치라 page.route mock 이 이긴다(서버 prefetch 없음).

test.describe.configure({ mode: "serial" });

// 전략 목록/상세 겸용 fixture — StrategyListItemSchema(list) + StrategyResponseSchema(detail)
// 양쪽을 만족(초과 키는 zod 가 strip)한다. §3 전략 select 채움용.
const MOCK_PBR_STRATEGY = {
  id: "947bc980-0000-4000-a000-000000000001",
  name: "PbR pivot reversal",
  description: null,
  pine_source: "//@version=5\nstrategy('PbR', overlay=true)\n",
  pine_version: "v5",
  parse_status: "ok",
  parse_errors: null,
  timeframe: "1h",
  symbol: "BTCUSDT",
  tags: [],
  trading_sessions: [],
  settings: null,
  pine_declared_qty: null,
  is_archived: false,
  created_at: "2026-05-01T00:00:00+00:00",
  updated_at: "2026-05-01T00:00:00+00:00",
} as const;

const MOCK_HEIKINASHI_STRATEGY = {
  id: "947bc980-0000-4000-a000-000000000099",
  name: "heikinashi-bad",
  description: null,
  pine_source: "//@version=5\nstrategy('HA')\nheikinashi(request.security(...))\n",
  pine_version: "v5",
  parse_status: "unsupported",
  parse_errors: null,
  timeframe: "1h",
  symbol: "BTCUSDT",
  tags: [],
  trading_sessions: [],
  settings: null,
  pine_declared_qty: null,
  is_archived: false,
  created_at: "2026-05-01T00:00:00+00:00",
  updated_at: "2026-05-01T00:00:00+00:00",
} as const;

const MOCK_BACKTEST_ID = "b7000000-0000-4000-8000-000000000001";

const MOCK_BACKTEST_DETAIL = {
  id: MOCK_BACKTEST_ID,
  strategy_id: MOCK_PBR_STRATEGY.id,
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

// /backtests/[id] 상세 + /trades(빈) mock 라우팅 — 여러 시나리오 공유.
function routeBacktestDetail(
  page: Page,
  detail: typeof MOCK_BACKTEST_DETAIL,
) {
  return page.route(API_ROUTES.backtests, (route, request) => {
    const url = request.url();
    if (url.includes(`${MOCK_BACKTEST_ID}/trades`)) {
      return fulfillJson({ items: [], total: 0, limit: 200, offset: 0 })(route);
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

test.describe("Sprint 32 dogfood gate — Surface Trust Recovery", () => {
  // §1: chart shell visual + MDD 카드 노출
  test("backtest result — chart shell visible + MDD 카드", async ({ page }) => {
    await routeBacktestDetail(page, MOCK_BACKTEST_DETAIL);

    await page.goto(`/backtests/${MOCK_BACKTEST_ID}`, { timeout: 60_000 });

    // §1 chart shell — 2-pane visible (BL-169)
    await expect(page.getByTestId("equity-chart-v2")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("equity-pane-wrapper")).toBeVisible();
    await expect(page.getByTestId("drawdown-pane-wrapper")).toBeVisible();

    // §1 chart legend — Equity / Buy&Hold / Drawdown 3항목 (BL-170).
    // KeyStatsStrip(성과 요약)도 role=list 라 반드시 "차트 범례" 로 scope 한다.
    const legend = page.getByRole("list", { name: "차트 범례" });
    await expect(legend.getByRole("listitem")).toHaveCount(3, { timeout: 5_000 });

    // §2 MDD 카드 — leverage=1 정상 시나리오 → KeyStatsStrip "최대 낙폭" 카드 자체는 visible.
    await expect(page.getByText("최대 낙폭").first()).toBeVisible();
  });

  // §2 강한 시나리오: leverage>1 + 자본 초과 손실 → KeyStatsStrip "최대 낙폭" foot 에 캡션 표시.
  test("backtest result — MDD leverage 캡션 노출 (leverage 5x)", async ({
    page,
  }) => {
    const leveragedDetail = {
      ...MOCK_BACKTEST_DETAIL,
      config: { ...MOCK_BACKTEST_DETAIL.config, leverage: 5 },
      metrics: {
        ...MOCK_BACKTEST_DETAIL.metrics,
        max_drawdown: "-1.32",
        mdd_exceeds_capital: true,
      },
    };

    await routeBacktestDetail(page, leveragedDetail);

    await page.goto(`/backtests/${MOCK_BACKTEST_ID}`, { timeout: 60_000 });

    // BL-156 캡션 — buildMddCaption(leverage 5x + 자본 초과) → "leverage 5.0x · 자본 초과 손실".
    await expect(
      page.getByText(/leverage 5\.0x.*자본 초과 손실/),
    ).toBeVisible({ timeout: 15_000 });
  });

  // §3 error UX — heikinashi 선택 시 422 + friendly_message
  test("backtest form — 422 friendly_message for unsupported builtin", async ({
    page,
  }) => {
    await page.route(API_ROUTES.strategies, (route) =>
      fulfillJson({
        items: [MOCK_PBR_STRATEGY, MOCK_HEIKINASHI_STRATEGY],
        total: 2,
        page: 0,
        limit: 20,
        total_pages: 1,
      })(route),
    );

    // POST /api/v1/backtests → 422 with friendly_message
    await page.route(API_ROUTES.backtests, (route, request) => {
      if (request.method() === "POST") {
        return route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify({
            detail: {
              code: "STRATEGY_NOT_RUNNABLE",
              detail: "heikinashi 함수는 미지원입니다",
              unsupported_builtins: ["heikinashi", "request.security"],
              friendly_message:
                "heikinashi / request.security 는 Trust Layer 위반(결과 부정확 risk). PbR / RSI / EMA cross 같은 ADR-003 supported list 의 indicator 로 대체 가능합니다.",
            },
          }),
        });
      }
      return fulfillJson({ items: [], total: 0, limit: 20, offset: 0 })(route);
    });

    await page.goto("/backtests/new", { timeout: 60_000 });

    // form load — C 이식 헤더 "새 백테스트 실행" (heading substring "새 백테스트").
    await expect(
      page.getByRole("heading", { name: "새 백테스트" }),
    ).toBeVisible({ timeout: 15_000 });

    // strategy 선택 (heikinashi-bad) — C 이식은 native <select id="strategy-select">.
    // 폼은 strategy_id 외 전부 default 라 선택만으로 제출 가능.
    await page
      .locator("#strategy-select")
      .selectOption({ label: "heikinashi-bad" });

    // 실행 → 422 응답
    await page.getByTestId("backtest-submit").click({ force: true });

    // friendly_message 카드 visible (BL-163) — FormErrorInline 의 friendly-message 요소로 scope
    // (전략 chip/option/요약행에도 "heikinashi" 가 있어 전역 getByText 는 strict mode 위반).
    const friendly = page.getByTestId("backtest-form-friendly-message");
    await expect(friendly).toBeVisible({ timeout: 10_000 });
    await expect(friendly).toContainText(/Trust Layer 위반|ADR-003/);
  });

  // §4 axis labels + markers — AxisLabelBar (BL-171+172) + trades mount 시 chart 정상 렌더.
  // canvas pixel 검증은 out-of-scope (DOM 으로 검사 어려움) → axis-label-bar testid + 축 라벨
  // testid + trades 존재 시 equity-chart-v2 정상 렌더 검증.
  test("backtest result — axis labels visible + chart render with trades", async ({
    page,
  }) => {
    const tradesDetail = { ...MOCK_BACKTEST_DETAIL };

    await page.route(API_ROUTES.backtests, (route, request) => {
      const url = request.url();
      if (url.includes(`${MOCK_BACKTEST_ID}/trades`)) {
        // C 이식 TradeItemSchema — entry/exit + size/pnl/return_pct/fees. Response = {items,total,limit,offset}.
        return fulfillJson({
          items: [
            {
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
            },
          ],
          total: 1,
          limit: 200,
          offset: 0,
        })(route);
      }
      if (url.includes(`${MOCK_BACKTEST_ID}/progress`)) {
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
        return fulfillJson(tradesDetail)(route);
      }
      return fulfillJson({ items: [], total: 0, limit: 20, offset: 0 })(route);
    });

    await page.goto(`/backtests/${MOCK_BACKTEST_ID}`, { timeout: 60_000 });

    // BL-172 axis labels — equity / drawdown 두 pane 각각의 axis-label-bar
    await expect(page.getByTestId("axis-label-bar-equity")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("axis-label-bar-drawdown")).toBeVisible();

    // y-axis-label + x-axis-label — 단위 / 시간 단위 inline 표시
    await expect(page.getByTestId("y-axis-label").first()).toBeVisible();
    await expect(page.getByTestId("x-axis-label").first()).toBeVisible();

    // BL-171 trade marker integration — chart mount 재확인 (trades prop → deriveTradeMarkers).
    await expect(page.getByTestId("equity-chart-v2")).toBeVisible();
  });
});
