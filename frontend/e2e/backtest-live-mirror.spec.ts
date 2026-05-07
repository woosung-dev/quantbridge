// BL-188 v3 백테스트 폼 ↔ Live Settings mirror E2E (D2 toggle / Nx reject / Pine override / sessions parity)
import { expect, test, type Page, type Route } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./fixtures/api-mock";

// Sprint 38 BL-188 v3 D — 통합 Playwright 5 case.
//
// 검증 의도:
// - jsdom unit (live-settings-mirror.test.tsx) 는 hook 단위 toggle 만 검증.
// - 실제 브라우저 reset() prefill + select onChange + Zod refine 422 분기는
//   Playwright 로만 회귀 가드 가능.
//
// API mock 패턴 — `/api/v1/strategies` (list) + `/api/v1/strategies/<id>` (detail) +
// `/api/v1/backtests` (POST) 만 mock. real backend 의존 0.
//
// chromium-authed project (storageState) — `/backtests/new` 이 protected route.
// playwright.config.ts L46 testMatch 정규식이 본 spec 을 등록.
//
// `serial mode` — 공유 storageState flake 차단 (dogfood-flow.spec.ts 패턴).
test.describe.configure({ mode: "serial" });

const STRATEGY_ID = "d0000000-0000-4000-d000-000000000001";

type LiveSettings = {
  schema_version: number;
  leverage: number;
  margin_mode: "cross" | "isolated";
  position_size_pct: number;
};

type StrategyDetail = {
  id: string;
  name: string;
  description: string | null;
  pine_source: string;
  pine_version: "v5" | "v6";
  parse_status: "ok" | "warning" | "error";
  parse_errors: null;
  timeframe: string | null;
  symbol: string | null;
  tags: string[];
  trading_sessions: string[];
  settings: LiveSettings | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  pine_declared_qty?: { type: string | null; value: number | null } | null;
};

const BASE_DETAIL: StrategyDetail = {
  id: STRATEGY_ID,
  name: "BL-188 v3 Mirror Test Strategy",
  description: null,
  pine_source: "//@version=5\nstrategy(\"t\", overlay=true)\n",
  pine_version: "v5",
  parse_status: "ok",
  parse_errors: null,
  timeframe: "1h",
  symbol: "BTCUSDT",
  tags: [],
  trading_sessions: [],
  settings: null,
  is_archived: false,
  created_at: "2026-05-07T00:00:00Z",
  updated_at: "2026-05-07T00:00:00Z",
};

// strategies list (BacktestForm 의 strategy select 채움) + 단일 항목.
const STRATEGIES_LIST = {
  items: [
    {
      id: STRATEGY_ID,
      name: BASE_DETAIL.name,
      tags: [],
      parse_status: "ok",
      pine_version: "v5",
      timeframe: BASE_DETAIL.timeframe,
      symbol: BASE_DETAIL.symbol,
      trading_sessions: [],
      is_archived: false,
      parse_errors: null,
      settings: null,
      created_at: BASE_DETAIL.created_at,
      updated_at: BASE_DETAIL.updated_at,
    },
  ],
  total: 1,
  page: 0,
  limit: 20,
  total_pages: 1,
};

// 시나리오별 strategy detail 을 라우터 핸들러에 주입. /api/v1/strategies/<id>
// (단건) 와 list (`/api/v1/strategies?...`) 를 trailing wildcard 로 분기.
function routeStrategies(detail: StrategyDetail) {
  return async (page: Page) => {
    await page.route(API_ROUTES.strategies, (route: Route) => {
      const url = route.request().url();
      // 단건 detail 패턴: `/api/v1/strategies/<uuid>` (다음 segment 가 query 또는 끝)
      if (url.includes(`/strategies/${STRATEGY_ID}`)) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(detail),
        });
      }
      // list (default)
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STRATEGIES_LIST),
      });
    });
    // backtests POST — 모든 case 가 submit 까지 가지 않으므로 noop OK.
    await page.route(API_ROUTES.backtests, fulfillJson({ items: [], total: 0, page: 0, page_size: 20 }));
  };
}

test.describe("backtest live mirror — BL-188 v3 D", () => {
  // CASE 1: Live 1x 30% strategy → Live mirror 배지 + 30% prefill.
  test("Live 1x 30% strategy → 30% prefill + Live mirror 배지", async ({ page }) => {
    // Pine indicator (declaration kind=indicator) + Live settings 1x 30%.
    const detail: StrategyDetail = {
      ...BASE_DETAIL,
      settings: {
        schema_version: 1,
        leverage: 1,
        margin_mode: "cross",
        position_size_pct: 30,
      },
      pine_declared_qty: null,
    };
    await routeStrategies(detail)(page);

    await page.goto(`/backtests/new?strategy_id=${STRATEGY_ID}`);
    await expect(page.getByRole("heading", { name: "새 백테스트" })).toBeVisible({
      timeout: 10_000,
    });

    // BacktestForm useStrategy fetch → reset() prefill 도착까지 대기.
    await expect(page.getByTestId("live-settings-badge-live")).toBeVisible({
      timeout: 10_000,
    });
    // Live 1x prefill: position_size_pct readonly input value=30.
    const pctInput = page.getByTestId("position-size-pct-input");
    await expect(pctInput).toHaveValue("30");
  });

  // CASE 2: Live 3x isolated → mirror 차단 + Manual 입력 enabled.
  test("Live 3x isolated → mirror 차단 + Manual 입력 가능", async ({ page }) => {
    const detail: StrategyDetail = {
      ...BASE_DETAIL,
      settings: {
        schema_version: 1,
        leverage: 3,
        margin_mode: "isolated",
        position_size_pct: 25,
      },
      pine_declared_qty: null,
    };
    await routeStrategies(detail)(page);

    await page.goto(`/backtests/new?strategy_id=${STRATEGY_ID}`);
    await expect(page.getByRole("heading", { name: "새 백테스트" })).toBeVisible({
      timeout: 10_000,
    });

    // Mirror blocked badge.
    await expect(page.getByTestId("live-settings-badge-blocked")).toBeVisible({
      timeout: 10_000,
    });
    // Manual 입력 enabled — default_qty_type select + value input.
    const qtyTypeSelect = page.getByTestId("default-qty-type-select");
    const qtyValueInput = page.getByTestId("default-qty-value-input");
    await expect(qtyTypeSelect).toBeEnabled();
    await expect(qtyValueInput).toBeEnabled();
  });

  // CASE 3: Pine `strategy(default_qty_type=cash, default_qty_value=5000)` → Pine
  // override 배지 + 폼 disabled.
  test("Pine declared default_qty 명시 → Pine override 배지 + 폼 disabled", async ({
    page,
  }) => {
    const detail: StrategyDetail = {
      ...BASE_DETAIL,
      pine_source:
        '//@version=5\nstrategy("t", overlay=true, default_qty_type=strategy.cash, default_qty_value=5000)\n',
      pine_declared_qty: { type: "strategy.cash", value: 5000 },
      // Live settings 도 1x 명시 — Pine override 가 무조건 우선임을 검증.
      settings: {
        schema_version: 1,
        leverage: 1,
        margin_mode: "cross",
        position_size_pct: 50,
      },
    };
    await routeStrategies(detail)(page);

    await page.goto(`/backtests/new?strategy_id=${STRATEGY_ID}`);
    await expect(page.getByRole("heading", { name: "새 백테스트" })).toBeVisible({
      timeout: 10_000,
    });

    // Pine override 배지.
    await expect(page.getByTestId("live-settings-badge-pine")).toBeVisible({
      timeout: 10_000,
    });
    // 폼 disabled — qty type select + qty value input.
    const qtyTypeSelect = page.getByTestId("default-qty-type-select");
    const qtyValueInput = page.getByTestId("default-qty-value-input");
    await expect(qtyTypeSelect).toBeDisabled();
    await expect(qtyValueInput).toBeDisabled();
  });

  // CASE 4: Manual toggle → Live → Manual 전환 시 position_size_pct 영역이 사라지고
  // default_qty_* enabled. 사용자가 Manual 로 회귀해 직접 입력 가능.
  test("Live → Manual toggle → default_qty_* 입력 enabled + Live 영역 disappears", async ({
    page,
  }) => {
    const detail: StrategyDetail = {
      ...BASE_DETAIL,
      settings: {
        schema_version: 1,
        leverage: 1,
        margin_mode: "cross",
        position_size_pct: 30,
      },
      pine_declared_qty: null,
    };
    await routeStrategies(detail)(page);

    await page.goto(`/backtests/new?strategy_id=${STRATEGY_ID}`);
    await expect(page.getByTestId("live-settings-badge-live")).toBeVisible({
      timeout: 10_000,
    });

    // sizing-source select 가 Live 일 때 manual 로 전환.
    const sourceSelect = page.getByTestId("sizing-source-select");
    await expect(sourceSelect).toBeVisible();
    await sourceSelect.selectOption("manual");

    // Manual 배지 + default_qty_* enabled + position_size_pct input 사라짐.
    await expect(page.getByTestId("live-settings-badge-manual")).toBeVisible({
      timeout: 5_000,
    });
    const qtyTypeSelect = page.getByTestId("default-qty-type-select");
    const qtyValueInput = page.getByTestId("default-qty-value-input");
    await expect(qtyTypeSelect).toBeEnabled();
    await expect(qtyValueInput).toBeEnabled();
    await expect(page.getByTestId("position-size-pct-input")).toHaveCount(0);
  });

  // CASE 5: trading_sessions=[asia] strategy → 폼 prefill (asia checked,
  // london/ny unchecked). Strategy.trading_sessions 단일 reference 정합.
  test("trading_sessions=[asia] strategy → asia checkbox prefill", async ({
    page,
  }) => {
    const detail: StrategyDetail = {
      ...BASE_DETAIL,
      trading_sessions: ["asia"],
      settings: null,
      pine_declared_qty: null,
    };
    await routeStrategies(detail)(page);

    await page.goto(`/backtests/new?strategy_id=${STRATEGY_ID}`);
    await expect(page.getByRole("heading", { name: "새 백테스트" })).toBeVisible({
      timeout: 10_000,
    });
    // sessions section 가 prefill 도착할 때까지 대기 — useStrategy data 로드 후
    // useEffect reset() 가 trading_sessions 채움. data-testid 가 wrapping <label>
    // 에 부착되어 있으므로 toBeChecked() 는 inner <input type="checkbox"> 매칭 필요.
    const asiaInput = page.locator('[data-testid="session-checkbox-asia"] input');
    const londonInput = page.locator('[data-testid="session-checkbox-london"] input');
    const nyInput = page.locator('[data-testid="session-checkbox-ny"] input');
    await expect(asiaInput).toBeChecked({ timeout: 10_000 });
    await expect(londonInput).not.toBeChecked();
    await expect(nyInput).not.toBeChecked();
  });
});
