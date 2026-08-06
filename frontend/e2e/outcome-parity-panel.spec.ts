import { expect, test, type Page } from "@playwright/test";

import { API_ROUTES, fulfillJson, makeLiveSessionState } from "./fixtures/api-mock";

// BL-608 — outcome-parity 패널 e2e 안전망 (그전까지 `frontend/e2e/**` 에 이 문자열 0건).
//
// ★로케이터는 **data-testid 만** 쓴다 (BL-597 규약). 상세가 열린 `/trading` 에는 `<table>` 이
// 5개 있고 「산출 불가」 는 페이지에서 11회 매치된다(2026-08-06 qa 프로브 실측) — 느슨한
// role/text 로케이터는 스코프끼리도 헷갈린다. 스코프는 `outcome-parity-{session,strategy}-*`
// 접두로 가르고, 정체성은 `live-session-detail-<uuid>` 로 못 박는다.
//
// 픽스처는 2026-08-06 소크 실측 응답의 형태 그대로다 — **세션 축 매칭 0 + 커버리지 `null`**,
// **전략 축 매칭 41 + 51자리 Decimal**. 이 비대칭이 BL-606(경고 스코프 맹목) 과
// BL-607(원문 Decimal 오버플로) 을 동시에 세우는 조합이다.

test.describe.configure({ mode: "serial" });

const STRATEGY_ID = "c0000000-0000-4000-8000-000000000001";
const SESSION_ID = "e0000000-0000-4000-8000-0000000000a6";

const MOCK_BYBIT_DEMO_ACCOUNT = {
  id: "a0000000-0000-4000-b000-000000000001",
  exchange: "bybit",
  mode: "demo",
  label: "Bybit Demo",
  api_key_masked: "***masked***",
  created_at: "2026-08-06T00:00:00Z",
} as const;

const MOCK_STRATEGY = {
  id: STRATEGY_ID,
  name: "BTC RSI Mean Reversion",
  tags: [],
  parse_status: "ok",
  updated_at: "2026-08-06T00:00:00Z",
};

const INACTIVE_SESSION = {
  id: SESSION_ID,
  user_id: "a0000000-0000-4000-a000-000000000001",
  strategy_id: STRATEGY_ID,
  exchange_account_id: MOCK_BYBIT_DEMO_ACCOUNT.id,
  symbol: "BTC/USDT",
  interval: "1m" as const,
  is_active: false,
  last_evaluated_bar_time: "2026-08-06T01:03:00Z",
  created_at: "2026-08-06T01:06:00Z",
  deactivated_at: "2026-08-06T01:04:00Z",
  deactivated_reason: "user_stopped",
};

// 51자리 — qa 증거(`overflow.json`)의 최악 사례. scrollWidth 551px vs clientWidth 66px.
const LONG_SD_NET = "1.2713870047249048479614767686509482542467350726347";
const LONG_NOTIONAL = "153223.9543200000000000";

const EMPTY_SESSION_SCOPE = {
  matched_count: 0,
  expected_gross: "0",
  actual_net: "0",
  decomposable_count: 0,
  decomposable_expected_gross: null,
  execution_gap: null,
  cost: null,
  decomposable_actual_net: null,
  actual_gross: null,
  round_trip_notional: null,
  effective_cost_pct_per_leg: null,
  effective_cost_pct_round_trip: null,
  edge_pct_round_trip: null,
  cost_to_edge_ratio: null,
  undecomposed_count: 0,
  undecomposed_net: "0",
  expected_only_count: 0,
  expected_only_gross: "0",
  expected_only_pending_count: 0,
  expected_only_failed_count: 0,
  expected_only_dispatched_count: 0,
  actual_only_count: 0,
  actual_only_net: "0",
  ledger_only_count: 0,
  ledger_only_net: "0",
  inferred_attribution_count: 0,
  match_coverage_pct: null,
  decomposition_coverage_pct: null,
  sample_n: 0,
  sample_mean_net: null,
  sample_sd_net: null,
  sample_required_n: null,
  sample_sufficient: false,
  ratio_sample_n: 0,
  ratio_sample_required_n: null,
  ratio_sample_sufficient: false,
};

const LIVE_STRATEGY_SCOPE = {
  ...EMPTY_SESSION_SCOPE,
  matched_count: 41,
  expected_gross: "30.72856076",
  actual_net: "-73.55319202",
  decomposable_count: 41,
  decomposable_expected_gross: "30.72856076",
  execution_gap: "-19.9238407600000000",
  cost: "-84.3579120200000000",
  decomposable_actual_net: "-73.55319202",
  actual_gross: "10.8047200000000000",
  round_trip_notional: LONG_NOTIONAL,
  effective_cost_pct_per_leg: "0.0551",
  effective_cost_pct_round_trip: "0.1101",
  edge_pct_round_trip: "-0.0960",
  cost_to_edge_ratio: "1.1468966839272191793043545467600224483092392650181",
  expected_only_count: 68,
  expected_only_gross: "20",
  expected_only_pending_count: 0,
  expected_only_failed_count: 0,
  expected_only_dispatched_count: 68,
  match_coverage_pct: "36.607142857142857142857142857",
  decomposition_coverage_pct: "100",
  sample_n: 41,
  sample_mean_net: "-1.7939802931707317073170731707317073170731707317073",
  sample_sd_net: LONG_SD_NET,
  sample_required_n: 30,
  sample_sufficient: true,
  ratio_sample_n: 41,
  ratio_sample_required_n: 30,
  ratio_sample_sufficient: true,
};

const OUTCOME_PARITY_RESPONSE = {
  session_id: SESSION_ID,
  session: EMPTY_SESSION_SCOPE,
  strategy: LIVE_STRATEGY_SCOPE,
  unattributed_count: 3,
  inferred_attribution_count: 0,
  ledger_supported: true,
  strategy_session_count: 31,
  assumption: {
    source: "house_default",
    taker_fee_pct: "0.055",
    slippage_pct: "0.05",
    maker_fee_pct: "0.02",
    implied_round_trip_pct: "0.21",
  },
};

// ★상세 하위 경로를 **먼저** 등록한다. 뒤에 등록한 catch-all 이 우선 매치되고
// `route.fallback()` 으로 여기로 넘어온다 (live-session-flow.spec.ts 와 같은 패턴).
async function mockTradingPage(page: Page) {
  await page.route(
    API_ROUTES.strategies,
    fulfillJson({ items: [MOCK_STRATEGY], total: 1, page: 0, page_size: 20 }),
  );
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [MOCK_BYBIT_DEMO_ACCOUNT] }));
  await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

  await page.route(
    `**/api/v1/live-sessions/${SESSION_ID}/state**`,
    fulfillJson(makeLiveSessionState({ sessionId: SESSION_ID })),
  );
  await page.route(`**/api/v1/live-sessions/${SESSION_ID}/events**`, fulfillJson({ items: [] }));
  await page.route(
    `**/api/v1/live-sessions/${SESSION_ID}/alert-rules**`,
    fulfillJson({ items: [], total: 0 }),
  );
  await page.route(
    `**/api/v1/live-sessions/${SESSION_ID}/outcome-parity**`,
    fulfillJson(OUTCOME_PARITY_RESPONSE),
  );

  await page.route(API_ROUTES.liveSessions, (route, request) => {
    const url = request.url();
    if (
      url.includes(`/live-sessions/${SESSION_ID}/state`) ||
      url.includes(`/live-sessions/${SESSION_ID}/events`) ||
      url.includes(`/live-sessions/${SESSION_ID}/alert-rules`) ||
      url.includes(`/live-sessions/${SESSION_ID}/outcome-parity`)
    ) {
      return route.fallback();
    }
    return fulfillJson({ items: [INACTIVE_SESSION], total: 1 })(route);
  });
}

async function openSessionDetail(page: Page) {
  await mockTradingPage(page);
  await page.goto("/trading?tab=live-sessions");

  const card = page.getByTestId(`inactive-live-session-${SESSION_ID}`);
  await expect(card).toBeVisible({ timeout: 15_000 });
  await card.click();

  // 정체성 앵커 — 이 uuid 의 상세가 **정확히 하나** 열려 있어야 한다.
  await expect(page.getByTestId(`live-session-detail-${SESSION_ID}`)).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByTestId(`live-session-detail-${SESSION_ID}`)).toHaveCount(1);
  await expect(page.getByTestId("outcome-parity-panel")).toHaveCount(1);
}

test.describe("outcome parity panel", () => {
  // BL-606 — 세션 축이 완전히 비어도 패널 머리 경고는 침묵한다(전략 축에 매칭이 있으므로).
  // 그 침묵을 스코프 카드 배너가 메우는지 화면에서 잰다.
  test("세션 축 매칭 0 · 전략 축 매칭 41 — 세션 카드가 스스로 무표본을 알린다", async ({
    page,
  }) => {
    await openSessionDetail(page);

    const banner = page.getByTestId("outcome-parity-session-no-matched-banner");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("이 세션에는 매칭된 청산이 0건입니다.");
    await expect(banner).toContainText("이 세션의 청산이 한 건도 포함되지 않습니다.");

    // 매칭이 있는 전략 축에는 배너가 없다 — 배너가 무조건 뜨는 장식이 아님을 고정한다.
    await expect(page.getByTestId("outcome-parity-strategy-no-matched-banner")).toHaveCount(0);
    // 패널 머리 경고는 이 조합에서 뜨지 않는다(현행 의미 동결 — 두 스코프가 함께 빌 때만).
    await expect(page.getByTestId("outcome-parity-unmatched-warning")).toHaveCount(0);
  });

  // BL-606 부수 — 세션 축 전항이 「산출 불가」인데 전략 워터폴이 값으로 채워져 있다.
  test("세션 축은 산출 불가, 전략 축은 값 — 두 스코프가 섞이지 않는다", async ({ page }) => {
    await openSessionDetail(page);

    await expect(page.getByTestId("outcome-parity-session-coverage")).toHaveText("산출 불가");
    await expect(page.getByTestId("outcome-parity-session-waterfall-expected")).toHaveText(
      "산출 불가",
    );
    await expect(page.getByTestId("outcome-parity-session-matched-count")).toHaveText("0건");

    await expect(page.getByTestId("outcome-parity-strategy-coverage")).toHaveText("36.61%");
    await expect(page.getByTestId("outcome-parity-strategy-matched-count")).toHaveText("41건");
    await expect(page.getByTestId("outcome-parity-strategy-scope-badge")).toHaveText("세션 31건");
  });

  // BL-607 — 표시 계층 반올림. 값 자체는 `title` 로 보존되고, 화면 폭 안에 들어온다.
  test("긴 Decimal 은 반올림해 보여주고 원문은 title 로 남긴다", async ({ page }) => {
    await openSessionDetail(page);

    const sd = page.getByTestId("outcome-parity-strategy-sample-sd-net");
    await expect(sd).toHaveText("1.2714");
    await expect(sd.locator("[title]")).toHaveAttribute("title", LONG_SD_NET);

    const notional = page.getByTestId("outcome-parity-strategy-round-trip-notional");
    await expect(notional).toHaveText("153223.9543");
    await expect(notional.locator("[title]")).toHaveAttribute("title", LONG_NOTIONAL);

    // 폭도 직접 잰다 — 텍스트 단언만으로는 "화면에서 잘리는가" 를 못 잰다.
    // qa 실측 원문 렌더는 scrollWidth **551px**(clientWidth 66px, 8.3배)였다. 150px 상한은
    // 폰트·DPI 가 달라져도 원문 복귀를 반드시 잡고, 반올림된 6자리는 여유롭게 통과한다.
    const scrollWidth = await sd.evaluate((el) => el.scrollWidth);
    expect(scrollWidth).toBeLessThan(150);
  });
});
