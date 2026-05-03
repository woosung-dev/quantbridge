import { expect, test } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./fixtures/api-mock";

// Sprint 26: BE ExchangeName enum 은 'bybit' (not 'bybit_futures' — historical fixture
// 와 다름). LiveSessionForm.allowedAccounts 가 정확히 'bybit' + 'demo' filter.
const MOCK_BYBIT_DEMO_ACCOUNT = {
  id: "a0000000-0000-4000-c000-000000000001",
  exchange: "bybit",
  mode: "demo",
  label: "Bybit Demo",
  api_key_masked: "***masked***",
  created_at: "2026-05-04T00:00:00Z",
} as const;

// Sprint 26 — Live Session E2E 회귀 가드.
//
// dogfood-flow 패턴 미러링 — 핵심 element 검증 + serial mode (공유 storageState flake 차단).
// 깊은 interaction (PnL chart datapoint, 5건 quota tooltip 등) 은 라이브 dogfood 단계.
//
// 시나리오 (3):
// 1. Live Sessions tab 진입 + 빈 상태 (TradingEmptyState 미러)
// 2. Bybit Demo notice + form 보임 (mode mismatch 시 disabled)
// 3. quota 도달 (5건) → submit disabled

test.describe.configure({ mode: "serial" });

const STRATEGY_ID = "s0000000-0000-4000-c000-000000000001";

const MOCK_STRATEGY = {
  id: STRATEGY_ID,
  name: "BTC RSI Mean Reversion",
  tags: [],
  parse_status: "ok",
  updated_at: "2026-05-04T00:00:00Z",
};

test.describe("live session flow", () => {
  // 시나리오 1: tab 진입 + 빈 상태
  test("Live Sessions tab — 빈 상태 안내 표시", async ({ page }) => {
    await page.route(
      API_ROUTES.strategies,
      fulfillJson({
        items: [MOCK_STRATEGY],
        total: 1,
        page: 0,
        page_size: 20,
      }),
    );
    await page.route(
      API_ROUTES.exchangeAccounts,
      fulfillJson({ items: [MOCK_BYBIT_DEMO_ACCOUNT] }),
    );
    await page.route(
      API_ROUTES.liveSessions,
      fulfillJson({ items: [], total: 0 }),
    );
    await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
    await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

    await page.goto("/trading?tab=live-sessions");

    // 빈 상태 안내
    await expect(page.getByTestId("live-session-empty")).toBeVisible({
      timeout: 15_000,
    });

    // Bybit Demo notice 가 form 위에 보임
    await expect(
      page.getByTestId("live-session-bybit-demo-notice"),
    ).toBeVisible();
  });

  // 시나리오 2: form submit 버튼 enabled (Bybit Demo 계정 + 0건 active)
  test("Live Sessions form — Bybit Demo 계정 + 0건 active → submit enabled", async ({
    page,
  }) => {
    await page.route(
      API_ROUTES.strategies,
      fulfillJson({
        items: [MOCK_STRATEGY],
        total: 1,
        page: 0,
        page_size: 20,
      }),
    );
    await page.route(
      API_ROUTES.exchangeAccounts,
      fulfillJson({ items: [MOCK_BYBIT_DEMO_ACCOUNT] }),
    );
    await page.route(
      API_ROUTES.liveSessions,
      fulfillJson({ items: [], total: 0 }),
    );
    await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
    await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

    await page.goto("/trading?tab=live-sessions");

    const submitBtn = page.getByTestId("live-session-submit");
    await expect(submitBtn).toBeVisible({ timeout: 15_000 });
    // strategies / accounts 데이터 도착 후 enabled 됨 — disabled 가 풀리는지만 확인
    await expect(submitBtn).toBeEnabled({ timeout: 5_000 });
  });

  // 시나리오 3: 5건 quota 도달 → submit disabled
  test("Live Sessions form — 5건 quota 도달 시 submit disabled", async ({
    page,
  }) => {
    const fiveActive = Array.from({ length: 5 }, (_, i) => ({
      id: `e0000000-0000-4000-c000-00000000000${i}`,
      user_id: "u0000000-0000-4000-a000-000000000001",
      strategy_id: STRATEGY_ID,
      exchange_account_id: MOCK_BYBIT_DEMO_ACCOUNT.id,
      symbol: `BTC${i}/USDT`,
      interval: "1m" as const,
      is_active: true,
      last_evaluated_bar_time: null,
      created_at: "2026-05-04T00:00:00Z",
      deactivated_at: null,
    }));

    await page.route(
      API_ROUTES.strategies,
      fulfillJson({
        items: [MOCK_STRATEGY],
        total: 1,
        page: 0,
        page_size: 20,
      }),
    );
    await page.route(
      API_ROUTES.exchangeAccounts,
      fulfillJson({ items: [MOCK_BYBIT_DEMO_ACCOUNT] }),
    );
    await page.route(
      API_ROUTES.liveSessions,
      fulfillJson({ items: fiveActive, total: 5 }),
    );
    await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
    await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

    await page.goto("/trading?tab=live-sessions");

    const submitBtn = page.getByTestId("live-session-submit");
    await expect(submitBtn).toBeVisible({ timeout: 15_000 });
    await expect(submitBtn).toBeDisabled();
  });
});
