// BL-551 — 라이브 세션 상세를 URL 로 열 수 있어야 한다
//
// 착수 시점 실측: 선택은 `trading-cockpit.tsx` 의 `useState` 가 쥐고 있었고 trading 트리
// 전체에 `useSearchParams` 가 0건이었다. 새로고침하면 선택이 사라지고 특정 세션으로 링크할
// 수단이 없었다.
//
// ★목록 밖 세션은 원리상 열 수 없다 — `GET /live-sessions/{id}` 단건 엔드포인트가 없고
//   목록은 활성 전체 + 최근 종료 20건뿐이다. 그래서 그 경우는 이미 있는
//   `live-session-stopped-notice` 로 떨어지는 것이 정답이고, 그것이 이 파일의 음성 대조다.
//
// chromium-authed project — Clerk storageState 필요. API 는 전부 mock 이라 DB 무관.

import { expect, test } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./fixtures/api-mock";
import { MOCK_OUTCOME_PARITY } from "./fixtures/outcome-parity";

// z.uuid() 준수 — variant nibble 은 [89ab] 여야 파싱을 통과한다.
const ACCOUNT_ID = "a0000000-0000-4000-b000-000000000011";
const STRATEGY_ID = "c0000000-0000-4000-8000-000000000011";
const SESSION_ID = "d0000000-0000-4000-8000-000000000011";
const GONE_ID = "d0000000-0000-4000-8000-0000000000ff";

const MOCK_ACCOUNT = {
  id: ACCOUNT_ID,
  exchange: "bybit",
  mode: "demo",
  label: "Bybit Demo",
  api_key_masked: "***masked***",
  created_at: "2026-05-04T00:00:00Z",
};

const MOCK_STRATEGY = {
  id: STRATEGY_ID,
  name: "Deeplink probe strategy",
  tags: [],
  parse_status: "ok",
  updated_at: "2026-05-04T00:00:00Z",
};

const MOCK_SESSION = {
  id: SESSION_ID,
  user_id: "a0000000-0000-4000-a000-000000000001",
  strategy_id: STRATEGY_ID,
  exchange_account_id: ACCOUNT_ID,
  symbol: "BTC/USDT",
  interval: "1m" as const,
  is_active: true,
  last_evaluated_bar_time: "2026-07-30T11:59:00Z",
  created_at: "2026-07-30T10:00:00Z",
  deactivated_at: null,
  deactivated_reason: null,
};

test.beforeEach(async ({ page }) => {
  await page.route(
    API_ROUTES.strategies,
    fulfillJson({ items: [MOCK_STRATEGY], total: 1, page: 0, page_size: 20 }),
  );
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [MOCK_ACCOUNT] }));
  await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

  // ★상세 하위 경로를 먼저 등록한다. 뒤에 등록한 catch-all 이 우선 매치되고 `route.fallback()`
  //   으로 여기로 넘어온다 (live-session-flow.spec.ts 와 같은 패턴). 목록 payload 로 상세를
  //   대신하면 zod parse 가 깨져 거짓 양성이 난다.
  await page.route(
    `**/api/v1/live-sessions/${SESSION_ID}/state**`,
    fulfillJson({
      session_id: SESSION_ID,
      evaluated: true,
      schema_version: 1,
      last_strategy_state_report: {},
      total_closed_trades: 0,
      total_realized_pnl: "0",
      equity_curve: [],
      updated_at: "2026-07-30T12:00:00Z",
    }),
  );
  await page.route(`**/api/v1/live-sessions/${SESSION_ID}/events**`, fulfillJson({ items: [] }));
  await page.route(
    `**/api/v1/live-sessions/${SESSION_ID}/alert-rules**`,
    fulfillJson({ items: [], total: 0 }),
  );
  await page.route(
    `**/api/v1/live-sessions/${SESSION_ID}/positions**`,
    fulfillJson({ items: [] }),
  );
  // ★codex G6 발견 3. `LiveSessionDetail` 은 `OutcomeParityPanel` 을 **항상** 렌더하고
  //   (`live-session-detail.tsx:238`) 그 패널은 `OutcomeParityResponseSchema` 를 요구한다.
  //   catch-all 이 목록 payload 를 돌려주면 패널만 조용히 오류 상태가 되고, 루트 testid 만
  //   보는 시험은 그대로 초록이다. 형식이 맞는 응답을 준다.
  await page.route(
    `**/api/v1/live-sessions/${SESSION_ID}/outcome-parity**`,
    fulfillJson(MOCK_OUTCOME_PARITY),
  );

  await page.route(API_ROUTES.liveSessions, (route, request) => {
    const url = request.url();
    if (
      /\/live-sessions\/[^/]+\/(state|events|alert-rules|positions|outcome-parity)/.test(url)
    ) {
      return route.fallback();
    }
    return fulfillJson({ items: [MOCK_SESSION], total: 1 })(route);
  });
});

test("?session=<id> 로 진입하면 상세 패널이 열린다", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto(`/trading?session=${SESSION_ID}`, { timeout: 60_000 });

  await expect(page.getByTestId(`live-session-detail-${SESSION_ID}`)).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByTestId("live-session-stopped-notice")).toHaveCount(0);
  // ★루트 testid 만 보면 하위 패널이 조용히 오류 상태여도 초록이다(codex G6 발견 3).
  //   실제 오류 표면 하나를 함께 못 박는다.
  await expect(page.getByTestId("outcome-parity-panel")).toBeVisible({ timeout: 30_000 });
  expect(consoleErrors).toEqual([]);
});

test("목록 밖 id 로 진입하면 중단 안내가 뜬다", async ({ page }) => {
  // ★음성 대조. 딥링크가 "무슨 id 든 상세를 연다" 로 번지지 않는지 본다.
  await page.goto(`/trading?session=${GONE_ID}`, { timeout: 60_000 });

  await expect(page.getByTestId("live-session-stopped-notice")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId(`live-session-detail-${SESSION_ID}`)).toHaveCount(0);
});

test("세션을 클릭한 뒤 새로고침해도 같은 상세가 열린다", async ({ page }) => {
  // ★공유 가능성의 실증. 선택이 URL 에 실려야만 새로고침을 넘어 살아남는다.
  await page.goto("/trading", { timeout: 60_000 });

  await page
    .getByTestId(`live-session-${SESSION_ID}`)
    .getByRole("button")
    .first()
    .click();

  await expect(page.getByTestId(`live-session-detail-${SESSION_ID}`)).toBeVisible({ timeout: 30_000 });
  await expect(page).toHaveURL(new RegExp(`[?&]session=${SESSION_ID}`));

  await page.reload();

  await expect(page.getByTestId(`live-session-detail-${SESSION_ID}`)).toBeVisible({ timeout: 30_000 });
});
