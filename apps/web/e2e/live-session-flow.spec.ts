import { expect, test } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./fixtures/api-mock";

// Sprint 26: BE ExchangeName enum 은 'bybit' (not 'bybit_futures' — historical fixture
// 와 다름). LiveSessionForm.allowedAccounts 가 정확히 'bybit' + 'demo' filter.
const MOCK_BYBIT_DEMO_ACCOUNT = {
  // z.uuid()(ExchangeAccountSchema.id)는 variant nibble [89ab]만 허용 → 'c000'은 reject 되어
  // accounts parse 실패 → allowedAccounts 0 → submit disabled. variant nibble 을 'b'로 정정한다.
  id: "a0000000-0000-4000-b000-000000000001",
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
// 시나리오 (4):
// 1. Live Sessions tab 진입 + 빈 상태 (TradingEmptyState 미러)
// 2. Bybit Demo notice + form 보임 (mode mismatch 시 disabled)
// 3. quota 도달 (5건) → submit disabled
// 4. BL-484 — 종료된 세션 선택 → 목록 카드와 상세 배지에 **종료 사유**가 보인다

test.describe.configure({ mode: "serial" });

// z.uuid() 준수 — 's'는 hex 아님, 'c'는 non-RFC variant. 둘 다 정정한다.
const STRATEGY_ID = "c0000000-0000-4000-8000-000000000001";

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
    await page.route(API_ROUTES.liveSessions, fulfillJson({ items: [], total: 0 }));
    await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
    await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

    await page.goto("/trading?tab=live-sessions");

    // 빈 상태 안내
    await expect(page.getByTestId("live-session-empty")).toBeVisible({
      timeout: 15_000,
    });

    // Bybit Demo notice 가 form 위에 보임
    await expect(page.getByTestId("live-session-bybit-demo-notice")).toBeVisible();
  });

  // 시나리오 2: form submit 버튼 enabled (Bybit Demo 계정 + 0건 active)
  test("Live Sessions form — Bybit Demo 계정 + 0건 active → submit enabled", async ({ page }) => {
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
    await page.route(API_ROUTES.liveSessions, fulfillJson({ items: [], total: 0 }));
    await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
    await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

    await page.goto("/trading?tab=live-sessions");

    const submitBtn = page.getByTestId("live-session-submit");
    await expect(submitBtn).toBeVisible({ timeout: 15_000 });
    // strategies / accounts 데이터 도착 후 enabled 됨 — disabled 가 풀리는지만 확인
    await expect(submitBtn).toBeEnabled({ timeout: 5_000 });
  });

  // 시나리오 3: 5건 quota 도달 → submit disabled
  test("Live Sessions form — 5건 quota 도달 시 submit disabled", async ({ page }) => {
    const fiveActive = Array.from({ length: 5 }, (_, i) => ({
      // z.uuid()(LiveSessionSchema) 준수 — id variant nibble 'c'→'8', user_id 'u'(non-hex)→'a'.
      id: `e0000000-0000-4000-8000-00000000000${i}`,
      user_id: "a0000000-0000-4000-a000-000000000001",
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
    await page.route(API_ROUTES.liveSessions, fulfillJson({ items: fiveActive, total: 5 }));
    await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
    await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

    await page.goto("/trading?tab=live-sessions");

    const submitBtn = page.getByTestId("live-session-submit");
    await expect(submitBtn).toBeVisible({ timeout: 15_000 });
    await expect(submitBtn).toBeDisabled();
  });

  // 시나리오 4: BL-484 — 종료된 세션을 골랐을 때 "왜 죽었는지" 가 화면에 있다.
  //
  // ★고치기 전 상태 — 사유는 Slack/Telegram 으로만 나가고 DB·API·화면에 없었다.
  // 알림을 놓치면 세션이 멈춘 이유를 화면 어디에서도 알 수 없었다.
  test("종료된 세션 — 목록 카드와 상세 배지에 종료 사유가 보인다", async ({ page }) => {
    const INACTIVE_ID = "e0000000-0000-4000-8000-0000000000f1";
    const inactiveSession = {
      id: INACTIVE_ID,
      user_id: "a0000000-0000-4000-a000-000000000001",
      strategy_id: STRATEGY_ID,
      exchange_account_id: MOCK_BYBIT_DEMO_ACCOUNT.id,
      symbol: "BTC/USDT",
      interval: "1m" as const,
      is_active: false,
      last_evaluated_bar_time: "2026-07-30T11:59:00Z",
      created_at: "2026-07-30T10:00:00Z",
      deactivated_at: "2026-07-30T12:00:00Z",
      deactivated_reason: "equity_exhausted",
    };

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
    await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
    await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

    // ★상세 하위 경로를 **먼저** 등록한다. 뒤에 등록한 catch-all 이 우선 매치되고
    // `route.fallback()` 으로 여기로 넘어온다 (sprint46-tier1 과 같은 패턴).
    // 목록 payload 로 상세 응답을 대신하면 zod parse 가 깨져 배지만 보이는
    // 거짓 양성이 된다 — 그래서 각 경로에 형식이 맞는 응답을 준다.
    await page.route(
      `**/api/v1/live-sessions/${INACTIVE_ID}/state**`,
      fulfillJson({
        session_id: INACTIVE_ID,
        evaluated: true,
        schema_version: 1,
        last_strategy_state_report: {},
        total_closed_trades: 0,
        total_realized_pnl: "0",
        equity_curve: [],
        updated_at: "2026-07-30T12:00:00Z",
      }),
    );
    await page.route(`**/api/v1/live-sessions/${INACTIVE_ID}/events**`, fulfillJson({ items: [] }));
    await page.route(
      `**/api/v1/live-sessions/${INACTIVE_ID}/alert-rules**`,
      fulfillJson({ items: [], total: 0 }),
    );

    await page.route(API_ROUTES.liveSessions, (route, request) => {
      const url = request.url();
      if (
        url.includes(`/live-sessions/${INACTIVE_ID}/state`) ||
        url.includes(`/live-sessions/${INACTIVE_ID}/events`) ||
        url.includes(`/live-sessions/${INACTIVE_ID}/alert-rules`)
      ) {
        return route.fallback();
      }
      return fulfillJson({ items: [inactiveSession], total: 1 })(route);
    });

    await page.goto("/trading?tab=live-sessions");

    // (a) 목록 카드 — 종료 세션 섹션에 한국어 사유가 붙는다.
    const listReason = page.getByTestId(`inactive-live-session-reason-${INACTIVE_ID}`);
    await expect(listReason).toBeVisible({ timeout: 15_000 });
    await expect(listReason).toHaveText("자본 소진");

    // (b) 그 카드를 고르면 상세가 열리고 배지 옆에 같은 사유가 보인다.
    await page.getByTestId(`inactive-live-session-${INACTIVE_ID}`).click();
    await expect(page.getByTestId("live-session-ended-badge")).toBeVisible();
    await expect(page.getByTestId("live-session-ended-reason")).toHaveText("자본 소진");
  });
});
