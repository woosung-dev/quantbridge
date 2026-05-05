import { expect, test } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./fixtures/api-mock";

// Sprint 32 — Surface Trust Recovery dogfood gate.
//
// codex G.0 P1-2 surgery: BL-157 live-smoke 가 public pages only / backend down 전제 /
// 4xx-5xx 무시 / unexpected error <5 허용 → chart/form/result PR dogfood 회귀 검출 불가.
// 본 gate 는 authed `/backtests/new` → run → result render → chart interaction 까지
// 통합 시나리오 검증.
//
// 검증 영역:
//   §1 chart shell — equity-chart-v2 / equity-pane-wrapper / drawdown-pane-wrapper / Legend (BL-169+170)
//   §2 MDD caption — mdd-leverage-caption (BL-156)
//   §3 error UX — friendly_message + unsupported_builtins (BL-163)
//   §4 marker tooltip — placeholder (Worker C BL-171+172 머지 후 활성화)
//
// 의존: Sprint 25 dogfood-flow.spec.ts 패턴 + chromium-authed project + storageState.

test.describe.configure({ mode: "serial" });

const MOCK_PBR_STRATEGY = {
  id: "947bc980-0000-4000-a000-000000000001",
  name: "PbR pivot reversal",
  pine_script: "// PbR strategy",
  is_runnable: true,
  unsupported_builtins: [],
  user_id: "user_test",
  created_at: "2026-05-01T00:00:00Z",
  updated_at: "2026-05-01T00:00:00Z",
} as const;

const MOCK_HEIKINASHI_STRATEGY = {
  id: "947bc980-0000-4000-a000-000000000099",
  name: "heikinashi-bad",
  pine_script: "// uses heikinashi(security)",
  is_runnable: false,
  unsupported_builtins: ["heikinashi", "request.security"],
  user_id: "user_test",
  created_at: "2026-05-01T00:00:00Z",
  updated_at: "2026-05-01T00:00:00Z",
} as const;

const MOCK_BACKTEST_ID = "bt000000-0000-4000-bt00-000000000001";

const MOCK_BACKTEST_DETAIL = {
  id: MOCK_BACKTEST_ID,
  strategy_id: MOCK_PBR_STRATEGY.id,
  status: "completed",
  initial_capital: 10000,
  config: {
    fee_rate: 0.0006,
    slippage_rate: 0.0005,
    leverage: 1,
    margin_mode: "cross",
    funding_rate: 0,
  },
  metrics: {
    total_return: 0.1234,
    sharpe_ratio: 1.5,
    max_drawdown: -0.345,
    win_rate: 0.55,
    num_trades: 42,
    mdd_unit: "equity_ratio",
    mdd_exceeds_capital: false,
  },
  equity_curve: [
    { time: "2024-01-01T00:00:00Z", equity: 10000 },
    { time: "2024-02-01T00:00:00Z", equity: 10500 },
    { time: "2024-03-01T00:00:00Z", equity: 11234 },
  ],
  benchmark_equity: [
    { time: "2024-01-01T00:00:00Z", equity: 10000 },
    { time: "2024-02-01T00:00:00Z", equity: 10100 },
    { time: "2024-03-01T00:00:00Z", equity: 10200 },
  ],
  drawdown_curve: [
    { time: "2024-01-01T00:00:00Z", drawdown: 0 },
    { time: "2024-02-01T00:00:00Z", drawdown: -0.05 },
    { time: "2024-03-01T00:00:00Z", drawdown: -0.345 },
  ],
  created_at: "2026-05-01T00:00:00Z",
  updated_at: "2026-05-01T00:00:00Z",
};

test.describe("Sprint 32 dogfood gate — Surface Trust Recovery", () => {
  // §1 + §2: chart shell visual + MDD caption integration
  test("backtest result — chart shell visible + MDD caption", async ({
    page,
  }) => {
    // strategies list mock
    await page.route(API_ROUTES.strategies, (route, request) => {
      const url = request.url();
      if (url.includes(MOCK_PBR_STRATEGY.id)) {
        return fulfillJson(MOCK_PBR_STRATEGY)(route);
      }
      return fulfillJson({
        items: [MOCK_PBR_STRATEGY],
        total: 1,
        page: 0,
        page_size: 20,
      })(route);
    });

    // backtest detail mock
    await page.route(API_ROUTES.backtests, (route, request) => {
      const url = request.url();
      if (request.method() === "POST") {
        return fulfillJson({ id: MOCK_BACKTEST_ID, status: "queued" }, 202)(
          route,
        );
      }
      if (url.includes(MOCK_BACKTEST_ID)) {
        return fulfillJson(MOCK_BACKTEST_DETAIL)(route);
      }
      return fulfillJson({ items: [], total: 0, page: 0, page_size: 20 })(
        route,
      );
    });

    await page.goto(`/backtests/${MOCK_BACKTEST_ID}`);

    // §1 chart shell — 2-pane visible (BL-169)
    await expect(page.getByTestId("equity-chart-v2")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("equity-pane-wrapper")).toBeVisible();
    await expect(page.getByTestId("drawdown-pane-wrapper")).toBeVisible();

    // §1 chart legend — color/style 명시 (BL-170)
    // ChartLegend 는 role="list" + 3 listitem (Equity / Buy&Hold / Drawdown)
    const legendItems = page.getByRole("listitem");
    await expect(legendItems).toHaveCount(3, { timeout: 5_000 });

    // §2 MDD caption — leverage=1 정상 시나리오 → caption 없음 (정책)
    // (mdd_exceeds_capital=false + leverage=1 → BL-156 정책상 caption 미표시)
    // Max Drawdown 카드 자체는 visible
    await expect(page.getByText("Max Drawdown")).toBeVisible();
  });

  // §2 강한 시나리오: leverage>1 또는 자본 초과 손실 → caption 표시
  test("backtest result — MDD leverage caption visible (leverage 5x)", async ({
    page,
  }) => {
    const leveragedDetail = {
      ...MOCK_BACKTEST_DETAIL,
      config: { ...MOCK_BACKTEST_DETAIL.config, leverage: 5 },
      metrics: {
        ...MOCK_BACKTEST_DETAIL.metrics,
        max_drawdown: -1.32,
        mdd_exceeds_capital: true,
      },
    };

    await page.route(API_ROUTES.strategies, (route, request) => {
      if (request.url().includes(MOCK_PBR_STRATEGY.id)) {
        return fulfillJson(MOCK_PBR_STRATEGY)(route);
      }
      return fulfillJson({
        items: [MOCK_PBR_STRATEGY],
        total: 1,
        page: 0,
        page_size: 20,
      })(route);
    });

    await page.route(API_ROUTES.backtests, (route, request) => {
      if (request.url().includes(MOCK_BACKTEST_ID)) {
        return fulfillJson(leveragedDetail)(route);
      }
      return fulfillJson({ items: [], total: 0, page: 0, page_size: 20 })(
        route,
      );
    });

    await page.goto(`/backtests/${MOCK_BACKTEST_ID}`);

    // BL-156 caption — leverage 가정 또는 자본 초과 손실 표시
    await expect(page.getByTestId("mdd-leverage-caption")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("mdd-leverage-caption")).toContainText(
      /leverage|자본 초과|초과 손실/,
    );
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
        page_size: 20,
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
      return fulfillJson({ items: [], total: 0, page: 0, page_size: 20 })(
        route,
      );
    });

    await page.goto("/backtests/new");

    // form load
    await expect(page.getByText("백테스트 실행")).toBeVisible({
      timeout: 15_000,
    });

    // strategy 선택 (heikinashi-bad)
    // strategy dropdown 클릭 → 옵션 선택. Sprint 31 BL-167 default 6개월 적용 상태.
    // (UI 가 `<select>` 또는 shadcn Select — 양쪽 호환)
    const strategySelect = page.getByLabel(/strategy|전략/i).first();
    await strategySelect.click();
    await page.getByText("heikinashi-bad").click();

    // 실행 → 422 응답
    await page.getByRole("button", { name: /실행|run|backtest 실행/i }).click();

    // friendly_message 카드 visible (BL-163)
    await expect(
      page.getByText(/Trust Layer 위반|ADR-003|지원하지 않는|heikinashi/),
    ).toBeVisible({ timeout: 10_000 });
  });

  // §4 marker tooltip — placeholder, Worker C (BL-171+172) 머지 후 활성화
  test.skip("backtest result — trade marker hover tooltip [BLOCKED: Worker C 머지 대기]", async () => {
    // BL-171: filled (entry) / outline (exit) + hover tooltip
    // 활성화 조건: stage/h2-sprint32-C-marker-axis 머지 후
  });
});
