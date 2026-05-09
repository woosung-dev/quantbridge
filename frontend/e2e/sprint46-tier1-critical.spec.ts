// Sprint 46 Tier 1 critical e2e — Strategy CRUD/Backtest polling/share/Live polling/Trading order
//
// 목적: dogfood Phase 2 가 비-자동 검증으로 5/10 정체된 critical user journey 5종을
// chromium-authed (storageState) project 안에서 mock fixture 기반 회귀 가드.
//
// 본 spec 은 5 시나리오를 serial mode 로 묶어 storageState flake 차단 (dogfood-flow
// 패턴 미러).
//
// W2 prompt 와의 차이 (의도적 deviation):
//  #1 — strategy create wizard 는 422 를 발행하지 않고 parse preview API 가
//       unsupported_builtins 를 반환하는 구조이며 FormErrorInline (UL hint) 도 strategy
//       에는 적용되지 않는다 (Sprint 41 E 가 backtest-form 만 도입). 본 spec 은 prompt
//       의 핵심 의도 — "422 응답 + FormErrorInline 안 unsupported_builtins UL" — 를
//       그대로 검증하기 위해 backtest-form 422 → FormErrorInline UL → 정상 submit 시
//       InProgressCard 흐름을 본 시나리오로 사용한다.
//  #4 — `/live-sessions/[id]` 라우트는 존재하지 않고 `/trading?tab=live-sessions` 안에서
//       LiveSessionDetail 가 right-pane 에 mount 되므로 그 경로를 사용한다.

import { expect, test } from "@playwright/test";

import {
  API_ROUTES,
  MOCK_DEMO_ACCOUNT,
  fulfillJson,
  makeBacktestDetail,
  makeBacktestProgress,
  makeLiveSessionState,
  makeShareToken,
  makeUnsupported422,
} from "./fixtures/api-mock";

test.describe.configure({ mode: "serial" });

// UUID v4 variant nibble = [89abAB] (RFC 4122). Zod z.uuid() rejects 'd' / 'u' 등.
const STRATEGY_ID = "f0000000-0000-4000-8000-000000000001";
const BACKTEST_ID = "b0000000-0000-4000-8000-000000000001";
const LIVE_SESSION_ID = "c0000000-0000-4000-8000-000000000001";
const USER_ID = "a0000000-0000-4000-8000-000000000099";

const STRATEGY_DETAIL = {
  id: STRATEGY_ID,
  name: "Sprint 46 W2 Strategy",
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
  created_at: "2026-05-01T00:00:00+00:00",
  updated_at: "2026-05-01T00:00:00+00:00",
};

const STRATEGY_LIST_ITEM = {
  ...STRATEGY_DETAIL,
};

test.describe("Sprint 46 Tier 1 critical user journey", () => {
  // ─────────────────────────────────────────────────────────────────────────
  // #1 Strategy CRUD 심화 — backtest-form 422 unsupported_builtins UL → 수정 후
  // 정상 submit. FormErrorInline (Sprint 41 E) 가 backtest-form 안에서 unsupported
  // builtin list 를 ul li 로 렌더하는 패턴을 회귀 가드.
  // ─────────────────────────────────────────────────────────────────────────
  test("#1 Backtest form — 422 unsupported_builtins UL hint → fix → submit success", async ({
    page,
  }) => {
    let postCount = 0;
    await page.route(API_ROUTES.strategies, (route, request) => {
      const url = request.url();
      if (url.includes(`/strategies/${STRATEGY_ID}`) && request.method() === "GET") {
        return fulfillJson(STRATEGY_DETAIL)(route);
      }
      return fulfillJson({
        items: [STRATEGY_LIST_ITEM],
        total: 1,
        page: 0,
        limit: 20,
        total_pages: 1,
      })(route);
    });

    await page.route(API_ROUTES.backtests, (route, request) => {
      const method = request.method();
      const url = request.url();
      if (method === "POST" && !url.includes("/share")) {
        postCount += 1;
        // 첫 submit: 422 unsupported_builtins. 두 번째: 202 created.
        if (postCount === 1) {
          return route.fulfill({
            status: 422,
            contentType: "application/json",
            body: JSON.stringify(
              makeUnsupported422(["heikinashi", "request.security"]),
            ),
          });
        }
        return fulfillJson(
          {
            backtest_id: BACKTEST_ID,
            status: "queued",
            created_at: "2026-05-09T00:00:00+00:00",
          },
          202,
        )(route);
      }
      return fulfillJson({ items: [], total: 0, limit: 20, offset: 0 })(route);
    });

    await page.goto(`/backtests/new?strategy_id=${STRATEGY_ID}`, {
      timeout: 60_000,
    });
    await expect(page.getByTestId("backtest-form-layout")).toBeVisible({
      timeout: 30_000,
    });
    // 전략 detail fetch (useStrategy) 완료 → useEffect reset prefill 끝까지 대기.
    await expect(page.getByTestId("setup-summary-aside")).toBeVisible({
      timeout: 15_000,
    });

    // 첫 submit → 422 → FormErrorInline unsupported card.
    const firstPostPromise = page.waitForRequest(
      (req) =>
        req.method() === "POST" &&
        req.url().includes("/api/v1/backtests") &&
        !req.url().includes("/share"),
      { timeout: 15_000 },
    );
    await page.getByTestId("backtest-submit").click({ force: true });
    await firstPostPromise;

    const card = page.getByTestId("backtest-form-unsupported-card");
    await expect(card).toBeVisible({ timeout: 15_000 });
    // UL 안 li 항목 — heikinashi + request.security 두 hint 가 렌더되는지.
    await expect(card.locator("ul li")).toHaveCount(2);
    await expect(card).toContainText(/heikinashi/);

    // 두 번째 submit → 202 → setSubmitError(null) → 카드 사라짐 +
    // useCreateBacktest onSuccess router.push redirect 발생.
    const secondPostPromise = page.waitForRequest(
      (req) =>
        req.method() === "POST" &&
        req.url().includes("/api/v1/backtests") &&
        !req.url().includes("/share"),
      { timeout: 15_000 },
    );
    await page
      .locator('form[aria-label="backtest-form"]')
      .evaluate((f) => (f as HTMLFormElement).requestSubmit());
    await secondPostPromise;
    await expect(card).toBeHidden({ timeout: 15_000 });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // #2 Backtest polling 3단계 — queued → running → completed.
  // useBacktestProgress refetchInterval 30s 로 long-poll 이라 e2e 에선 page.reload()
  // 로 transition trigger (mock 응답 swap 후 강제 fetch). 각 단계마다 InProgressCard
  // 의 라벨 또는 chart 가 visible 한지 검증.
  // ─────────────────────────────────────────────────────────────────────────
  test("#2 Backtest polling — queued → running → completed transitions", async ({
    page,
  }) => {
    // Phase 1: queued.
    await page.route(API_ROUTES.backtests, (route, request) => {
      const url = request.url();
      if (url.includes(`/backtests/${BACKTEST_ID}/progress`)) {
        return fulfillJson(
          makeBacktestProgress({ id: BACKTEST_ID, status: "queued" }),
        )(route);
      }
      if (url.includes(`/backtests/${BACKTEST_ID}/trades`)) {
        return fulfillJson({ items: [], total: 0, limit: 200, offset: 0 })(
          route,
        );
      }
      if (url.includes(`/backtests/${BACKTEST_ID}`)) {
        return fulfillJson(
          makeBacktestDetail({
            id: BACKTEST_ID,
            strategyId: STRATEGY_ID,
            status: "queued",
          }),
        )(route);
      }
      return fulfillJson({ items: [], total: 0, limit: 20, offset: 0 })(route);
    });

    await page.goto(`/backtests/${BACKTEST_ID}`, { timeout: 60_000 });
    // InProgressCard 의 paragraph (배지 외 — 30초 폴링 안내 문구) 매칭.
    await expect(
      page.getByText(/대기 중입니다.*30초 간격 폴링/),
    ).toBeVisible({ timeout: 15_000 });

    // Phase 2: running. mock swap + reload (refetchInterval 30s 우회).
    await page.unroute(API_ROUTES.backtests);
    await page.route(API_ROUTES.backtests, (route, request) => {
      const url = request.url();
      if (url.includes(`/backtests/${BACKTEST_ID}/progress`)) {
        return fulfillJson(
          makeBacktestProgress({ id: BACKTEST_ID, status: "running" }),
        )(route);
      }
      if (url.includes(`/backtests/${BACKTEST_ID}/trades`)) {
        return fulfillJson({ items: [], total: 0, limit: 200, offset: 0 })(
          route,
        );
      }
      if (url.includes(`/backtests/${BACKTEST_ID}`)) {
        return fulfillJson(
          makeBacktestDetail({
            id: BACKTEST_ID,
            strategyId: STRATEGY_ID,
            status: "running",
          }),
        )(route);
      }
      return fulfillJson({ items: [], total: 0, limit: 20, offset: 0 })(route);
    });

    await page.reload({ timeout: 60_000 });
    await expect(
      page.getByText(/실행 중입니다.*30초 간격 폴링/),
    ).toBeVisible({ timeout: 15_000 });

    // Phase 3: completed + metrics + equity_curve → chart shell + tabs visible.
    await page.unroute(API_ROUTES.backtests);
    await page.route(API_ROUTES.backtests, (route, request) => {
      const url = request.url();
      if (url.includes(`/backtests/${BACKTEST_ID}/progress`)) {
        return fulfillJson(
          makeBacktestProgress({ id: BACKTEST_ID, status: "completed" }),
        )(route);
      }
      if (url.includes(`/backtests/${BACKTEST_ID}/trades`)) {
        return fulfillJson({ items: [], total: 0, limit: 200, offset: 0 })(
          route,
        );
      }
      if (url.includes(`/backtests/${BACKTEST_ID}`)) {
        return fulfillJson(
          makeBacktestDetail({
            id: BACKTEST_ID,
            strategyId: STRATEGY_ID,
            status: "completed",
            withMetrics: true,
            withEquity: true,
          }),
        )(route);
      }
      return fulfillJson({ items: [], total: 0, limit: 20, offset: 0 })(route);
    });

    await page.reload({ timeout: 60_000 });

    // chart shell + 24-metric panel 의 대표 tab 들 visible.
    await expect(page.getByTestId("equity-chart-v2")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByRole("tab", { name: "성과 지표" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "거래 분석" })).toBeVisible();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // #3 Backtest share flow — ShareButton 의 클라이언트 사이드 상태 머신
  // (공유 → "공유 중" + 취소 → DELETE → "공유" 복원) + revoke fallback UI.
  //
  // NOTE: /share/backtests/{token} 은 Server Component 가 직접 fetch 하는 SSR
  // 이라 page.route 가 가로채지 못한다 (Playwright 는 브라우저 트래픽만 mock).
  // 본 테스트는 in-app share button 상태 머신만 검증. 공개 페이지 410/404 는
  // share-page.test.tsx (vitest) 가 이미 커버.
  // ─────────────────────────────────────────────────────────────────────────
  test("#3 Backtest share button — create → 공유 중 → revoke → 공유 복원", async ({
    page,
  }) => {
    const shareToken = "share-46-w2-token";

    await page.route(API_ROUTES.backtests, (route, request) => {
      const url = request.url();
      const method = request.method();

      if (url.includes(`/backtests/${BACKTEST_ID}/share`) && method === "POST") {
        return fulfillJson(makeShareToken(BACKTEST_ID, shareToken))(route);
      }
      if (
        url.includes(`/backtests/${BACKTEST_ID}/share`) &&
        method === "DELETE"
      ) {
        return route.fulfill({ status: 204, body: "" });
      }
      if (url.includes(`/backtests/${BACKTEST_ID}/progress`)) {
        return fulfillJson(
          makeBacktestProgress({ id: BACKTEST_ID, status: "completed" }),
        )(route);
      }
      if (url.includes(`/backtests/${BACKTEST_ID}/trades`)) {
        return fulfillJson({ items: [], total: 0, limit: 200, offset: 0 })(
          route,
        );
      }
      if (url.includes(`/backtests/${BACKTEST_ID}`)) {
        return fulfillJson(
          makeBacktestDetail({
            id: BACKTEST_ID,
            strategyId: STRATEGY_ID,
            status: "completed",
            withMetrics: true,
            withEquity: true,
          }),
        )(route);
      }
      return fulfillJson({ items: [], total: 0, limit: 20, offset: 0 })(route);
    });

    await page.goto(`/backtests/${BACKTEST_ID}`, { timeout: 60_000 });

    const shareBtn = page.getByRole("button", { name: "공유" });
    await expect(shareBtn).toBeVisible({ timeout: 30_000 });

    await shareBtn.click();

    // 클릭 → POST /share → onSuccess 가 sharedUrl state set → "공유 중" + 취소 버튼.
    await expect(page.getByText("공유 중")).toBeVisible({ timeout: 15_000 });
    const revokeBtn = page.getByRole("button", { name: /공유 취소/ });
    await expect(revokeBtn).toBeVisible();

    // 공유 취소 클릭 → DELETE 204 → onSuccess 가 sharedUrl null 로 복원 → "공유" 버튼 재표시.
    await revokeBtn.click();
    await expect(page.getByRole("button", { name: "공유" })).toBeVisible({
      timeout: 15_000,
    });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // #4 Live Session detail polling — /trading?tab=live-sessions right-pane.
  // 활성 세션 select → LiveSessionDetail mount → 초기 state mock (closed=2)
  // → state mock swap (closed=5) → 5s 폴링 trigger 후 신규 값 visible.
  // ─────────────────────────────────────────────────────────────────────────
  test("#4 Live session detail — equity polling 5s tick", async ({ page }) => {
    const session = {
      id: LIVE_SESSION_ID,
      user_id: USER_ID,
      strategy_id: STRATEGY_ID,
      exchange_account_id: MOCK_DEMO_ACCOUNT.id,
      symbol: "BTCUSDT",
      interval: "1m" as const,
      is_active: true,
      last_evaluated_bar_time: null,
      created_at: "2026-05-09T00:00:00+00:00",
      deactivated_at: null,
    };

    await page.route(
      API_ROUTES.strategies,
      fulfillJson({
        items: [STRATEGY_LIST_ITEM],
        total: 1,
        page: 0,
        limit: 20,
        total_pages: 1,
      }),
    );
    await page.route(
      API_ROUTES.exchangeAccounts,
      fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }),
    );
    await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));
    await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));

    // events 응답 — 빈 timeline 으로 시작.
    await page.route(
      `**/api/v1/live-sessions/${LIVE_SESSION_ID}/events**`,
      fulfillJson({ items: [] }),
    );

    // session list — 단일 active session.
    await page.route(API_ROUTES.liveSessions, (route, request) => {
      const url = request.url();
      // /live-sessions/{id}/state 는 별도 핸들러로 위임.
      if (url.includes(`/live-sessions/${LIVE_SESSION_ID}/state`)) {
        return route.fallback();
      }
      if (url.includes(`/live-sessions/${LIVE_SESSION_ID}/events`)) {
        return route.fallback();
      }
      return fulfillJson({ items: [session], total: 1 })(route);
    });

    // state 응답 swap-able — 초기 closed=2.
    let stateClosed = 2;
    let statePnl = "100";
    await page.route(
      `**/api/v1/live-sessions/${LIVE_SESSION_ID}/state**`,
      (route) => {
        return fulfillJson(
          makeLiveSessionState({
            sessionId: LIVE_SESSION_ID,
            closedTrades: stateClosed,
            realizedPnl: statePnl,
          }),
        )(route);
      },
    );

    await page.goto("/trading?tab=live-sessions", { timeout: 60_000 });

    // 활성 세션 list 의 select button 클릭 — symbol 텍스트 매칭.
    await expect(page.getByTestId(`live-session-${LIVE_SESSION_ID}`)).toBeVisible(
      { timeout: 30_000 },
    );
    await page
      .getByTestId(`live-session-${LIVE_SESSION_ID}`)
      .getByRole("button", { name: /BTCUSDT/ })
      .click();

    // detail panel mount — 초기 closed=2 / pnl=100.
    await expect(
      page.getByTestId(`live-session-detail-${LIVE_SESSION_ID}`),
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      page
        .getByTestId(`live-session-detail-${LIVE_SESSION_ID}`)
        .getByText("2", { exact: true }),
    ).toBeVisible();

    // mock swap — 다음 polling tick 부터 closed=5 / pnl=200.
    stateClosed = 5;
    statePnl = "200";

    // 5s polling tick (LIVE_SESSION_STATE_REFETCH_ACTIVE_MS) + 1s margin.
    await expect(
      page
        .getByTestId(`live-session-detail-${LIVE_SESSION_ID}`)
        .getByText("5", { exact: true }),
    ).toBeVisible({ timeout: 8_000 });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // #5 Trading order full flow — TestOrderDialog (NEXT_PUBLIC_ENABLE_TEST_ORDER=true).
  // sessionStorage 안 webhook secret 주입 → 다이얼로그 열기 → form 채우기 → POST
  // /api/v1/webhooks/{strategy_id}?token=... 발송 → HMAC token 검증 → 성공 후
  // orders mock 갱신 + invalidation refetch → 새 entry visible.
  // ─────────────────────────────────────────────────────────────────────────
  test("#5 Test order dialog — HMAC dispatch + orders panel reflects new entry", async ({
    page,
  }) => {
    interface OrderItem {
      id: string;
      symbol: string;
      side: "buy" | "sell";
      quantity: string;
      state: "pending" | "submitted" | "filled" | "rejected" | "cancelled";
      filled_price: string | null;
      exchange_order_id: string | null;
      error_message: string | null;
      created_at: string;
    }
    let ordersList: OrderItem[] = [
      {
        id: "a1110000-0000-4000-8000-000000000099",
        symbol: "ETHUSDT",
        side: "buy",
        quantity: "0.1",
        state: "filled",
        filled_price: "3000",
        exchange_order_id: "broker-existing-99",
        error_message: null,
        created_at: "2026-05-09T00:00:00+00:00",
      },
    ];

    await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));
    await page.route(
      API_ROUTES.exchangeAccounts,
      fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }),
    );
    await page.route(API_ROUTES.strategies, (route, request) => {
      if (request.method() === "GET") {
        return fulfillJson({
          items: [STRATEGY_LIST_ITEM],
          total: 1,
          page: 0,
          limit: 20,
          total_pages: 1,
        })(route);
      }
      return route.fallback();
    });
    await page.route(API_ROUTES.orders, (route) => {
      return fulfillJson({ items: ordersList, total: ordersList.length })(route);
    });

    // sessionStorage 에 webhook secret 주입 (storageKey = `qb-webhook-secret-{id}`).
    const secretInjection = {
      strategyId: STRATEGY_ID,
      secret: "test-webhook-secret-46",
      ttlMs: 30 * 60 * 1000,
    };
    await page.addInitScript((args) => {
      sessionStorage.setItem(
        `qb-webhook-secret-${args.strategyId}`,
        JSON.stringify({
          plaintext: args.secret,
          expiresAt: Date.now() + args.ttlMs,
        }),
      );
    }, secretInjection);

    // webhook POST intercept — HMAC token 검증.
    let capturedHmacToken: string | null = null;
    await page.route(API_ROUTES.webhooks, (route, request) => {
      const url = new URL(request.url());
      capturedHmacToken = url.searchParams.get("token");
      // submit 후 invalidation 으로 orders refetch 시 신규 항목 응답을 위해 list 갱신.
      ordersList = [
        {
          id: "a1110000-0000-4000-8000-000000000100",
          symbol: "BTCUSDT",
          side: "buy",
          quantity: "0.001",
          state: "submitted",
          filled_price: null,
          exchange_order_id: "broker-new-100",
          error_message: null,
          created_at: "2026-05-09T00:01:00+00:00",
        },
        ...ordersList,
      ];
      return fulfillJson(
        {
          id: "a1110000-0000-4000-8000-000000000100",
          order_id: "broker-new-100",
        },
        201,
      )(route);
    });

    await page.goto("/trading", { timeout: 60_000 });

    // 테스트 주문 button → dialog open.
    await page
      .getByRole("button", { name: /^테스트 주문$/ })
      .dispatchEvent("click");
    await expect(
      page.getByRole("heading", { name: "테스트 주문 (dogfood-only)" }),
    ).toBeVisible({ timeout: 15_000 });

    // 전략 select.
    await page.getByLabel("전략").click();
    await page
      .getByRole("option", { name: STRATEGY_DETAIL.name })
      .click();

    // 거래소 계정 select.
    await page.getByLabel("거래소 계정").click();
    await page.getByRole("option").first().click();

    // 수량 입력.
    await page.getByLabel(/수량/).fill("0.001");

    // 발송 → POST webhook.
    await page.getByRole("button", { name: /^발송$/ }).click();

    // dialog 닫힘 + sonner toast 성공.
    await expect(
      page.getByRole("heading", { name: "테스트 주문 (dogfood-only)" }),
    ).toBeHidden({ timeout: 15_000 });

    // HMAC token 64자 hex (SHA-256 hexdigest) 검증.
    expect(capturedHmacToken, "HMAC token query param").not.toBeNull();
    expect(capturedHmacToken!, "HMAC SHA-256 hex length").toHaveLength(64);
    expect(capturedHmacToken!, "HMAC hex 형식").toMatch(/^[0-9a-f]{64}$/);

    // invalidation 후 orders panel 신규 entry 표시 — broker-new-100 의 last 8 chars
    // ("-new-100") + (broker) suffix. broker-badge-real testid 가 두 개 (기존 + 신규)
    // 가 되어야 한다.
    await expect(page.getByTestId("broker-badge-real")).toHaveCount(2, {
      timeout: 15_000,
    });
  });
});
