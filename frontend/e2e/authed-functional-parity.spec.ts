// functional-parity 스프린트 e2e — 주문 취소 배선(A2) / nav-count 미체결 배지(B2) /
// strategy backtest_count 열(B1) / 대시보드 전략 링크 edit 재조준(A1) 회귀 가드.
//
// mock 원칙: API_ROUTES glob(orders 는 `**/api/v1/orders**` 라 /cancel 하위까지 커버)을
// 먼저 등록하고, 구체 라우트(/cancel POST)는 **마지막에 등록**해 우선시킨다
// (sprint55 스펙에서 실증된 Playwright 등록 역순 매칭 함정).

import { expect, test, type Page } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./fixtures/api-mock";

// UUID v4 variant nibble = [89abAB] (RFC 4122) — zod z.uuid() 통과 형식.
const PENDING_ID = "d0000000-0000-4000-8000-000000000f01";
const SUBMITTED_ID = "d0000000-0000-4000-8000-000000000f02";
const FILLED_ID = "d0000000-0000-4000-8000-000000000f03";
const STRATEGY_A_ID = "f0000000-0000-4000-8000-0000000000a1";

function makeOrder(opts: {
  id: string;
  state: "pending" | "submitted" | "filled";
  createdAt: string;
}) {
  return {
    id: opts.id,
    symbol: "BTC/USDT",
    side: "buy",
    state: opts.state,
    quantity: "0.01",
    filled_price: opts.state === "filled" ? "50000" : null,
    exchange_order_id: opts.state === "pending" ? null : "ex-1",
    error_message: null,
    created_at: opts.createdAt,
    reduce_only: false,
    trigger_price: null,
    trigger_by: null,
    take_profit: null,
    stop_loss: null,
    trigger_direction: null,
    oco_group_id: null,
    trailing_stop: null,
  };
}

const ORDER_PENDING = makeOrder({
  id: PENDING_ID,
  state: "pending",
  createdAt: "2026-07-23T03:00:00+00:00",
});
const ORDER_SUBMITTED = makeOrder({
  id: SUBMITTED_ID,
  state: "submitted",
  createdAt: "2026-07-23T02:00:00+00:00",
});
const ORDER_FILLED = makeOrder({
  id: FILLED_ID,
  state: "filled",
  createdAt: "2026-07-23T01:00:00+00:00",
});

function makeStrategyListItem(opts: {
  id: string;
  name: string;
  backtestCount?: number;
}) {
  return {
    id: opts.id,
    name: opts.name,
    description: null,
    pine_source: "//@version=5\nstrategy('t')\n",
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
    created_at: "2026-07-01T00:00:00+00:00",
    updated_at: "2026-07-01T00:00:00+00:00",
    ...(opts.backtestCount === undefined
      ? {}
      : { backtest_count: opts.backtestCount }),
  };
}

// StrategyListResponseSchema 봉투 = {items,total,page,limit,total_pages} 5필드 의무.
function makeStrategyListEnvelope(items: unknown[]) {
  return {
    items,
    total: items.length,
    page: 1,
    limit: 20,
    total_pages: 1,
  };
}

// 공용 셸(사이드바 nav-count 3종 + 코크핏)이 페치하는 목록들의 기본 mock.
// orders 는 URL 에 state 필터가 있으면(사이드바 미체결 배지) filtered total 을,
// 없으면(원장 FETCH_LIMIT=200) 전체 3건을 돌려준다.
async function mockShellRoutes(
  page: Page,
  opts?: { openOrdersTotal?: number },
) {
  const context = page.context();
  await context.route(
    API_ROUTES.strategies,
    fulfillJson(makeStrategyListEnvelope([])),
  );
  await context.route(API_ROUTES.backtests, fulfillJson({ items: [], total: 0 }));
  await context.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [] }));
  await context.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));
  await context.route(API_ROUTES.liveSessions, fulfillJson({ items: [], total: 0 }));
  await context.route(API_ROUTES.orders, async (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.has("state")) {
      await fulfillJson({ items: [], total: opts?.openOrdersTotal ?? 2 })(route);
      return;
    }
    await fulfillJson({
      items: [ORDER_PENDING, ORDER_SUBMITTED, ORDER_FILLED],
      total: 3,
    })(route);
  });
}

test.describe("functional-parity 회귀 가드", () => {
  test("A2 — pending 취소 클릭 → POST /orders/{id}/cancel 발사, filled 는 dim 셀", async ({
    page,
  }) => {
    await mockShellRoutes(page);
    let cancelPosted = false;
    // 구체 /cancel 라우트를 마지막 등록 — orders glob 보다 우선.
    await page.context().route("**/api/v1/orders/*/cancel", async (route) => {
      expect(route.request().method()).toBe("POST");
      expect(route.request().url()).toContain(`/orders/${PENDING_ID}/cancel`);
      cancelPosted = true;
      await fulfillJson({ ...ORDER_PENDING, state: "cancelled" })(route);
    });

    await page.goto("/orders");

    const pendingRow = page.locator("tr", { hasText: "대기" }).first();
    await expect(
      pendingRow.getByRole("button", { name: "주문 취소" }),
    ).toBeVisible();

    // filled 행은 취소 버튼 없이 dim "—" 셀.
    const filledRow = page.locator("tr", { hasText: "체결" }).first();
    await expect(
      filledRow.getByRole("button", { name: "주문 취소" }),
    ).toHaveCount(0);

    await pendingRow.getByRole("button", { name: "주문 취소" }).click();
    await expect.poll(() => cancelPosted).toBe(true);
  });

  test("A2 — submitted 취소 202 → '요청됨' 안내 toast, '취소됨' 완료 표기 금지", async ({
    page,
  }) => {
    await mockShellRoutes(page);
    await page.context().route("**/api/v1/orders/*/cancel", async (route) => {
      await fulfillJson(
        {
          order_id: SUBMITTED_ID,
          state: "submitted",
          detail: "exchange cancel requested",
        },
        202,
      )(route);
    });

    await page.goto("/orders");

    const submittedRow = page.locator("tr", { hasText: "전송" }).first();
    await submittedRow.getByRole("button", { name: "주문 취소" }).click();

    // 202 = 비동기 취소 접수 — "요청" 안내만, 완료("취소됨") 표기는 금지.
    await expect(
      page.getByText("거래소에 취소를 요청했습니다"),
    ).toBeVisible();
    await expect(page.getByText("취소됨", { exact: true })).toHaveCount(0);
  });

  test("B2 — 사이드바 주문 배지 = state 필터 total (미체결 수)", async ({
    page,
  }) => {
    await mockShellRoutes(page, { openOrdersTotal: 7 });

    await page.goto("/orders");

    // 원장은 전체 3건을 보여주지만, nav 배지는 filtered total 7 을 표시해야 한다.
    const ordersNav = page.getByRole("link", { name: /주문/ }).first();
    await expect(ordersNav.locator(".nav-count")).toHaveText("7");
  });

  // /strategies 는 서버 컴포넌트 프리페치(HydrationBoundary)라 Playwright 라우트 목이
  // Node-side fetch 를 가로채지 못한다 → 목 대신 라이브 구조 불변식으로 검증한다.
  // (값 정합의 외부 오라클 = DB COUNT 3점 대조는 dogfood 단계 몫.)
  test("B1 — 전략 목록 backtest_count 열이 라이브 렌더되고 전 행이 정수다 (빈칸 금지)", async ({
    page,
  }) => {
    await page.goto("/strategies");

    await expect(
      page.getByRole("columnheader", { name: "백테스트" }),
    ).toBeVisible();

    // perf-surface 가 성과 3열(td.num, 미완료 시 '—')을 추가했으므로 count 열만 정확히 겨냥한다.
    const countCells = page.locator('tbody tr td[data-testid="strategy-backtest-count"]');
    const n = await countCells.count();
    // 라이브 시드 DB(전략 목록) 전제 — 0행이면 침묵 통과가 아니라 실패로 드러낸다.
    expect(n).toBeGreaterThan(0);
    for (let i = 0; i < n; i++) {
      await expect(countCells.nth(i)).toHaveText(/^\d+$/);
    }
  });

  test("A1 — 대시보드 전략명 링크는 /strategies/{id}/edit 로 간다", async ({
    page,
  }) => {
    const context = page.context();
    await context.route(API_ROUTES.backtests, fulfillJson({ items: [], total: 0 }));
    await context.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [] }));
    await context.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));
    await context.route(API_ROUTES.liveSessions, fulfillJson({ items: [], total: 0 }));
    await context.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
    const detail = makeStrategyListItem({
      id: STRATEGY_A_ID,
      name: "FP Strategy A",
      backtestCount: 3,
    });
    await context.route(API_ROUTES.strategies, async (route) => {
      const url = new URL(route.request().url());
      // 상세 GET(/strategies/{uuid})은 단건, 그 외(목록/필터)는 봉투.
      if (/\/api\/v1\/strategies\/[0-9a-f-]{36}$/.test(url.pathname)) {
        await fulfillJson(detail)(route);
        return;
      }
      await fulfillJson(makeStrategyListEnvelope([detail]))(route);
    });

    await page.goto("/dashboard");

    await page
      .locator(`[data-testid="strategy-row-${STRATEGY_A_ID}"]`)
      .getByRole("link", { name: "FP Strategy A" })
      .click();

    await expect(page).toHaveURL(new RegExp(`/strategies/${STRATEGY_A_ID}/edit$`));
    // edit 페이지가 실제로 mount 됐는지 (404/에러 바운더리가 아닌지) 확인.
    await expect(page.getByText("FP Strategy A").first()).toBeVisible();
  });
});
