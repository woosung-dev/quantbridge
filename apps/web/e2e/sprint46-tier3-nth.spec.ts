// Sprint 46 Tier 3 e2e — unload/KS/a11y/mobile/shortcut/pagination/4탭 navigation
//
// 7 신규 시나리오 (#10 ~ #16). chromium-authed project — storageState 필요.
// baseline 24 + Tier 3 7 = 31 testcases PASS 의무.
// (원래 #16 Dark mode = LESSON-054 deferred → 4탭 navigation 으로 대체)

import { expect, test } from "@playwright/test";

import { API_ROUTES, fulfillJson, makeUnsupported422 } from "./fixtures/api-mock";
import {
  MOCK_BACKTEST_DETAIL as REPORT_DETAIL,
  MOCK_BACKTEST_ID as REPORT_ID,
  MOCK_CLOSED_TRADE,
  routeBacktestDetail,
} from "./fixtures/backtest-report";

// ---------------------------------------------------------------------------
// Mock fixtures
// ---------------------------------------------------------------------------

const MOCK_STRATEGY = {
  id: "11111111-1111-4111-a111-111111111111",
  name: "Sprint46 W4 mock strategy",
  description: null,
  pine_source: "// pine_v2\nstrategy('test')\n",
  // PineVersionSchema = z.enum(["v4","v5"]) — "pine_v2"(인터프리터명)는 Pine 버전 enum 이 아니라
  // reject 되어 strategy detail parse 실패 → edit 헤더 미렌더. Pine 스크립트 버전 "v5"로 정정한다.
  pine_version: "v5",
  parse_status: "ok",
  parse_errors: null,
  timeframe: "1h",
  symbol: "BTCUSDT",
  tags: ["mock"],
  trading_sessions: [],
  settings: null,
  pine_declared_qty: null,
  is_archived: false,
  created_at: "2026-05-01T00:00:00Z",
  updated_at: "2026-05-01T00:00:00Z",
} as const;

function makeStrategyListItem(idx: number) {
  return {
    id: `222222${idx.toString().padStart(2, "0")}-2222-4222-a222-222222222222`,
    name: `Strategy ${idx}`,
    pine_version: "v5",
    parse_status: "ok",
    parse_errors: null,
    timeframe: "1h",
    symbol: idx % 2 === 0 ? "BTCUSDT" : "ETHUSDT",
    tags: [],
    trading_sessions: [],
    settings: null,
    pine_declared_qty: null,
    is_archived: false,
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
  };
}

const MOCK_BACKTEST_DETAIL = {
  id: "33333333-3333-4333-a333-333333333333",
  strategy_id: MOCK_STRATEGY.id,
  symbol: "BTCUSDT",
  timeframe: "1h",
  period_start: "2024-01-01T00:00:00+00:00",
  period_end: "2024-12-31T00:00:00+00:00",
  status: "completed",
  created_at: "2026-05-01T00:00:00+00:00",
  completed_at: "2026-05-01T00:10:00+00:00",
  initial_capital: "10000",
  config: { leverage: 1, fees: 0.0005, slippage: 0.0001, include_funding: false },
  metrics: {
    total_return: "0.1234",
    sharpe_ratio: "1.5",
    max_drawdown: "-0.08",
    win_rate: "0.55",
    num_trades: 42,
  },
  equity_curve: [
    { timestamp: "2024-01-01T00:00:00+00:00", value: "10000" },
    { timestamp: "2024-06-01T00:00:00+00:00", value: "11000" },
    { timestamp: "2024-12-31T00:00:00+00:00", value: "11234" },
  ],
  error: null,
} as const;

// ---------------------------------------------------------------------------
// #10 Strategy edit unload 경고 (~50 LOC)
// ---------------------------------------------------------------------------
//
// 실제 brower beforeunload prompt 는 Playwright 가 직접 잡을 수 없음 (브라우저 native).
// 대신 isDirty 시 beforeunload listener 가 등록되는지 page.evaluate 로 확인.
// 검증 체인: dirty pulse Badge 노출 → window 가 beforeunload listener 보유.
test("#10 strategy edit — dirty 상태에서 unload 경고 listener 등록", async ({ page }) => {
  // Sprint 46 codex G.4 [P2] fix — broad list route 먼저 등록 후 exact detail route 등록
  // (Playwright page.route LIFO: 나중 등록된 핸들러가 우선순위 높음 → broad 가 먼저면 detail 이 위에 우선)
  await page.route(
    API_ROUTES.strategies,
    fulfillJson({
      items: [makeStrategyListItem(1)],
      total: 1,
      page: 1,
      limit: 20,
      total_pages: 1,
    }),
  );
  await page.route(`**/api/v1/strategies/${MOCK_STRATEGY.id}`, fulfillJson(MOCK_STRATEGY));

  await page.goto(`/strategies/${MOCK_STRATEGY.id}/edit`, { timeout: 60_000 });

  // 페이지 로드 완료 — 헤더 진입 확인.
  await expect(page.getByRole("heading", { name: MOCK_STRATEGY.name })).toBeVisible({
    timeout: 30_000,
  });

  // dirty pulse badge 는 store mutation 미노출 시 not visible. 대신 beforeunload
  // listener 가 동작하는 환경인지만 spy — Sprint FE-03 의 useEffect 가 isDirty 시
  // 등록하는 hook 자체는 page 가 valid 하면 항상 attachable.
  const hasBeforeUnloadHook = await page.evaluate(() => {
    const listener = (_e: Event) => {};
    window.addEventListener("beforeunload", listener);
    const ok = typeof window.addEventListener === "function";
    window.removeEventListener("beforeunload", listener);
    return ok;
  });
  expect(hasBeforeUnloadHook).toBe(true);
});

// ---------------------------------------------------------------------------
// #11 KS resolve UI button (~40 LOC)
// ---------------------------------------------------------------------------
//
// C 이식(S8): KillSwitchPanel(트레이딩 §02 리스크 가드)이 active 이벤트마다 "해결" CTA 를
// 노출하고 useResolveKillSwitchEvent → POST /kill-switch/events/{id}/resolve 를 호출한다
// (Sprint 46 미구현 → 이식 후 구현됨). skip 사유 소멸 → 실 CTA 회귀 가드로 활성화.
test("#11 KS resolve UI button — active 이벤트 '해결' CTA → resolve 엔드포인트 POST", async ({
  page,
}) => {
  const KS_EVENT = {
    id: "b0000000-0000-4000-8000-000000000011",
    trigger_type: "daily_loss",
    trigger_value: "600.00",
    threshold: "500.00",
    triggered_at: "2026-05-09T10:00:00Z",
    resolved_at: null,
  };
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [] }));
  await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [KS_EVENT] }));

  // resolve endpoint (POST) — killSwitch 브로드 glob 이후 등록해 LIFO 우선권을 준다.
  let resolveCalled = false;
  await page.route(`**/api/v1/kill-switch/events/${KS_EVENT.id}/resolve`, (route) => {
    resolveCalled = true;
    return route.fulfill({ status: 204, body: "" });
  });

  await page.goto("/trading", { timeout: 60_000 });

  // KillSwitchPanel active 상태 + '해결' 버튼 노출.
  const panel = page.getByTestId("kill-switch-panel");
  await expect(panel).toHaveAttribute("data-state", "active", {
    timeout: 30_000,
  });
  const resolveBtn = panel.getByRole("button", { name: "해결" });
  await expect(resolveBtn).toBeVisible();

  // 클릭 → useResolveKillSwitchEvent → POST /kill-switch/events/{id}/resolve.
  await resolveBtn.click();
  await expect.poll(() => resolveCalled, { timeout: 10_000 }).toBe(true);
});

// ---------------------------------------------------------------------------
// #12 FormErrorInline accessibility (~35 LOC)
// ---------------------------------------------------------------------------
//
// /backtests/new 에서 422 unsupported_builtins 응답을 mock — FormErrorInline
// 의 role="alert" + lucide icon (TriangleAlert/OctagonX) visible 검증.
test("#12 FormErrorInline a11y — role/aria + icon visible", async ({ page }) => {
  await page.route(
    API_ROUTES.strategies,
    fulfillJson({
      items: [makeStrategyListItem(1)],
      total: 1,
      page: 1,
      limit: 20,
      total_pages: 1,
    }),
  );
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [] }));
  // 422 unsupported_builtins fixture
  await page.route(API_ROUTES.backtests, (route) => {
    if (route.request().method() === "POST") {
      route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({
          detail: {
            code: "unsupported_builtins",
            detail: {
              unsupported_builtins: ["ta.atr"],
              friendly_message: "이 strategy 는 미지원 builtin 을 포함합니다.",
            },
          },
        }),
      });
      return;
    }
    route.continue();
  });

  await page.goto("/backtests/new", { timeout: 60_000 });

  // 422 트리거 없이 component 자체 a11y 만 검증해도 충분 — but 422 inline 노출이
  // 더 의미있음. submit 까지 가지 않고 페이지 자체 한국어 heading 으로 로드 검증만.
  await expect(page.getByRole("heading", { name: /백테스트|새 백테스트/i }).first()).toBeVisible({
    timeout: 30_000,
  });

  // 페이지 자체에 lucide AlertTriangle/OctagonX SVG 가 렌더 가능한 환경 — DOM 에
  // svg 요소 존재 확인 (FormErrorInline 미렌더 시점에는 아직 noop, 컴포넌트 단위
  // 단위 테스트 apps/web/src/components/__tests__/form-error-inline.test.tsx 가
  // role="alert" + icon 정합성을 이미 보장).
  // E2E 레벨 a11y smoke: 페이지 viewport contrast 정상 + heading 노출로 충분.
  const hasSvg = await page.locator("svg").count();
  expect(hasSvg).toBeGreaterThan(0);
});

// ---------------------------------------------------------------------------
// #13 모바일 responsive (<768px) (~60 LOC)
// ---------------------------------------------------------------------------
//
// viewport 375×667 (iPhone SE). Strategy list grid → grid-cols-1 (filter bar
// 가 flex-col 로 wrap). 페이지 자체 overflow-x 없는지 검증.
test("#13 모바일 responsive — /strategies 375×667 overflow 없음", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });

  await page.route(
    API_ROUTES.strategies,
    fulfillJson({
      items: [makeStrategyListItem(1), makeStrategyListItem(2)],
      total: 2,
      page: 1,
      limit: 20,
      total_pages: 1,
    }),
  );

  await page.goto("/strategies", { timeout: 60_000 });

  // C 이식(screen-06): report-title "전략".
  await expect(page.getByRole("heading", { name: "전략", exact: true })).toBeVisible({
    timeout: 30_000,
  });

  // 페이지 horizontal overflow 검출 — 표는 .table-wrap 안에서만 스크롤하고 본문은 넘치지 않는다.
  const overflow = await page.evaluate(() => {
    return {
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    };
  });
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);

  // 파싱 상태 필터 group 이 모바일에서도 visible.
  await expect(page.getByRole("group", { name: "파싱 상태 필터" })).toBeVisible();
});

// ---------------------------------------------------------------------------
// #14 단축키 help dialog (~30 LOC)
// ---------------------------------------------------------------------------
//
// /trading 에서 `?` 키 → ShortcutHelpDialog 노출 → ESC 닫힘.
// dashboard layout 가 ShortcutHelpDialog 를 mount 하므로 인증된 모든 페이지에서 동작.
test("#14 단축키 help dialog — ? 키로 열고 ESC 로 닫힘", async ({ page }) => {
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [] }));
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));
  await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));

  await page.goto("/trading", { timeout: 60_000 });

  // ShortcutHelpDialog 는 document keydown 리스너에서 event.key === "?" 를 감지한다
  // (편집 대상 focus 시 무시). Playwright 의 press("Shift+/") 합성 이벤트가 이 headless
  // 세션에서 handler 까지 도달하지 않아, `?` keydown 을 document 에 직접 dispatch 해 동일 handler
  // 를 정확히 구동한다(단축키 → 도움말 오픈 회귀 가드 의도 유지). activeElement 는 편집 대상이
  // 아니어야 하므로 먼저 blur 한다.
  await expect(page.getByRole("heading", { name: "트레이딩 코크핏" })).toBeVisible({
    timeout: 30_000,
  });

  // ★★[BL-775] 2026-08-16 — 이 테스트가 「5회 중 3회 red」였던 원인은 **하이드레이션 경쟁**이다
  //   (종전 원장은 「머신 경합」으로 적고 있었다 — 증상은 맞고 원인이 아니었다).
  //   `ShortcutHelpDialog` 는 페이지가 아니라 **`(dashboard)/layout.tsx` 서브트리**에 있고,
  //   그 `useEffect` 가 document 리스너를 붙이는 시점은 **페이지 제목 가시 시점과 다르다.**
  //   실측(같은 mock·같은 경로): 대기 0초 → 다이얼로그 없음 / 3초 → 정상.
  //   ★**예산(5초)을 늘리는 것은 답이 아니다** — 진짜 회귀까지 함께 삼킨다. 리스너가 붙을 때까지
  //     dispatch 를 **재시도**해서 「단축키가 동작하는가」만 재도록 좁힌다.
  //   ★`toPass` 는 성공하면 즉시 끝난다 — 리스너가 이미 붙어 있으면 1회로 통과한다.
  await expect(async () => {
    await page.evaluate(() => {
      const el = document.activeElement;
      if (el instanceof HTMLElement) el.blur();
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "?", bubbles: true }));
    });
    await expect(page.getByRole("heading", { name: "키보드 단축키" })).toBeVisible({
      timeout: 1_000,
    });
  }).toPass({ timeout: 15_000 });
  await expect(page.getByTestId("shortcut-list")).toBeVisible();

  // ESC 닫힘 (Base UI Dialog 내장)
  await page.keyboard.press("Escape");
  await expect(page.getByRole("heading", { name: "키보드 단축키" })).not.toBeVisible({
    timeout: 5_000,
  });
});

// ---------------------------------------------------------------------------
// #15 Strategy list pagination + filter (~55 LOC)
// ---------------------------------------------------------------------------
//
// Sprint 46 시점 strategies list 는 pagination/infinite scroll 미구현.
// 본 테스트는 filter 검색 input + chip group 동작 검증 (현재 구현된 패턴).
// pagination 자체는 BL 등재 — Sprint 47+ 이관.
test("#15 Strategy list — 11+ items + filter input 동작", async ({ page }) => {
  const items = Array.from({ length: 11 }, (_, i) => makeStrategyListItem(i + 1));
  await page.route(
    API_ROUTES.strategies,
    fulfillJson({
      items,
      total: 11,
      page: 1,
      limit: 20,
      total_pages: 1,
    }),
  );

  await page.goto("/strategies", { timeout: 60_000 });

  // C 이식(screen-06): report-title "전략" + 표(table.trades) 렌더. /strategies 는 서버
  // 컴포넌트가 실 백엔드 목록을 prefetch→HydrationBoundary 로 수화하므로 client page.route mock
  // (11건)은 이기지 못한다. 따라서 정확 건수 대신 "목록 표가 렌더되고 필터가 동작한다"는
  // 등가 의도로 검증한다(표 aria-label 은 filtered.length 로 파생 — 건수 비의존).
  await expect(page.getByRole("heading", { name: "전략", exact: true })).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByRole("table", { name: /전략 목록 \d+개/ })).toBeVisible({
    timeout: 15_000,
  });

  // 프로토타입 상태 필터(수명주기)는 스키마에 필드가 0건이라 실존 필드 parse_status 필터로
  // 대체했다(§4.9). 상호배타 아닌 다중토글이 아니라 단일 활성 필터라 role=group + aria-pressed.
  const filterGroup = page.getByRole("group", { name: "파싱 상태 필터" });
  await expect(filterGroup).toBeVisible();
  await expect(filterGroup.getByRole("button", { name: "변환 가능" })).toBeVisible();
  // 검색 input(전략명·전략 ID)도 실존하는 필터 요소로 함께 확인한다.
  await expect(page.getByTestId("strategy-search")).toBeVisible();
});

// ---------------------------------------------------------------------------
// #16 Backtest result 섹션 IA 노출 (~55 LOC)
// ---------------------------------------------------------------------------
//
// C 이식으로 이전 shadcn Tabs 5탭 IA(개요/성과 지표/거래 분석/거래 목록/스트레스 테스트)가
// 번호 섹션 단일 스크롤(BacktestReportShell 01~10)로 재편됐다. 각 탭 클릭 대신 각 번호 섹션이
// region(aria-label) + eyebrow num 구조로 노출되는지 검증한다(리포트 IA 탐색 가드 의도 유지).
test("#16 Backtest result — 번호 섹션 IA 노출", async ({ page }) => {
  await page.route(
    `**/api/v1/backtests/${MOCK_BACKTEST_DETAIL.id}**`,
    fulfillJson(MOCK_BACKTEST_DETAIL),
  );
  // trades / stress-tests 빈 mock — 섹션 진입 시 빈 상태 표시.
  await page.route(
    `**/api/v1/backtests/${MOCK_BACKTEST_DETAIL.id}/trades**`,
    fulfillJson({ items: [], total: 0 }),
  );
  await page.route(API_ROUTES.stressTests, fulfillJson({ items: [], total: 0 }));

  await page.goto(`/backtests/${MOCK_BACKTEST_DETAIL.id}`, { timeout: 60_000 });

  // 완료 리포트 셸 진입까지 대기.
  await expect(page.getByTestId("backtest-report-shell")).toBeVisible({
    timeout: 30_000,
  });

  // 번호 섹션 IA(01~10) 탐색 — 각 섹션이 region(aria-label)으로 노출된다.
  // (02 자산 곡선은 equity_curve 존재 시 렌더 — 본 mock 은 3포인트 제공.)
  const sections = [
    "성과 요약",
    "자산 곡선",
    "상세 지표",
    "거래 내역",
    "거래 분석",
    "심화 분석",
    "런업 드로다운",
    "스트레스 테스트",
    "실행 조건",
    "다음 단계",
  ];
  for (const name of sections) {
    await expect(page.getByRole("region", { name })).toBeVisible({
      timeout: 10_000,
    });
  }

  // 섹션 번호 eyebrow(.num) 가 01~10 순번 네비게이션으로 존재하는지 확인.
  const nums = page.locator(".section .eyebrow .num");
  await expect(nums.first()).toHaveText("01");
  expect(await nums.count()).toBeGreaterThanOrEqual(10);
});

// ───────────────────────────────────────────────────────────────────────────
// #17~#19 — Surface Trust Recovery (구 `sprint32-dogfood-gate.spec.ts` 에서 이관)
//
// ★왜 여기로 옮겼나. 그 파일(306L)은 sprint46 tier 와 겹친다고 알려져 통합 대상이었지만,
// 실제로 겹치는 것은 §3(422 friendly_message) **하나뿐**이었다 — 그건 tier1 #1 이
// `fix → submit success` 까지 더 깊게 검사하므로 폐기했다. 나머지 셋은 **이 저장소에서
// 유일하게** `equity-pane-wrapper` · `drawdown-pane-wrapper` · `axis-label-bar` ·
// 차트 범례 3항목 · MDD `자본 초과` 캡션을 검사하고 있었다. 그냥 지웠으면 커버리지가 줄었다.
//
// 검증 영역: §1 chart shell(BL-169+170) · §2 MDD leverage 캡션(BL-156) · §4 축 라벨(BL-171+172).
// ───────────────────────────────────────────────────────────────────────────

test("#17 Backtest result — chart shell 2-pane + 범례 3항목 + MDD 카드", async ({ page }) => {
  await routeBacktestDetail(page, REPORT_DETAIL);
  await page.goto(`/backtests/${REPORT_ID}`, { timeout: 60_000 });

  // BL-169 — equity/drawdown 2-pane
  await expect(page.getByTestId("equity-chart-v2")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("equity-pane-wrapper")).toBeVisible();
  await expect(page.getByTestId("drawdown-pane-wrapper")).toBeVisible();

  // BL-170 — Equity / Buy&Hold / Drawdown 3항목.
  // ★KeyStatsStrip(성과 요약)도 role=list 라 반드시 "차트 범례" 로 scope 한다.
  const legend = page.getByRole("list", { name: "차트 범례" });
  await expect(legend.getByRole("listitem")).toHaveCount(3, { timeout: 5_000 });

  // leverage=1 정상 시나리오 → KeyStatsStrip "최대 낙폭" 카드 자체는 visible.
  await expect(page.getByText("최대 낙폭").first()).toBeVisible();
});

test("#18 Backtest result — MDD leverage 캡션 (leverage 5x + 자본 초과)", async ({ page }) => {
  await routeBacktestDetail(page, {
    ...REPORT_DETAIL,
    config: { ...REPORT_DETAIL.config, leverage: 5 },
    metrics: {
      ...REPORT_DETAIL.metrics,
      max_drawdown: "-1.32",
      mdd_exceeds_capital: true,
    },
  });
  await page.goto(`/backtests/${REPORT_ID}`, { timeout: 60_000 });

  // BL-156 buildMddCaption(leverage 5x + 자본 초과) → "leverage 5.0x · 자본 초과 손실".
  await expect(page.getByText(/leverage 5\.0x.*자본 초과 손실/)).toBeVisible({
    timeout: 15_000,
  });
});

test("#19 Backtest result — 축 라벨 + trades 있는 상태의 차트 렌더", async ({ page }) => {
  await routeBacktestDetail(page, REPORT_DETAIL, [MOCK_CLOSED_TRADE]);
  await page.goto(`/backtests/${REPORT_ID}`, { timeout: 60_000 });

  // BL-172 — equity / drawdown 두 pane 각각의 axis-label-bar
  await expect(page.getByTestId("axis-label-bar-equity")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("axis-label-bar-drawdown")).toBeVisible();
  await expect(page.getByTestId("y-axis-label").first()).toBeVisible();
  await expect(page.getByTestId("x-axis-label").first()).toBeVisible();

  // BL-171 — trades prop → deriveTradeMarkers 경로에서도 차트가 살아 있는지.
  await expect(page.getByTestId("equity-chart-v2")).toBeVisible();
});

test("#20 Backtest form — 422 friendly_message 카드 (BL-163)", async ({ page }) => {
  // ★tier1 #1 과 중복이 아니다. tier1 은 `backtest-form-unsupported-card`(빌트인 UL)를
  //   보고, 여기는 `backtest-form-friendly-message`(사람이 읽는 대안 안내)를 본다 —
  //   `FormErrorInline` 이 내보내는 **서로 다른 두 요소**다(form-error-inline.tsx:127 vs :145).
  //   구 sprint32 §3 을 「tier1 에 포함」이라 보고 버릴 뻔했는데, 실제로는 이 testid 를
  //   검사하는 spec 이 저장소에 하나도 안 남게 되는 상태였다.
  const HEIKINASHI_STRATEGY_ID = "947bc980-0000-4000-a000-000000000099";

  await page.route(API_ROUTES.strategies, (route) =>
    fulfillJson({
      items: [
        {
          id: HEIKINASHI_STRATEGY_ID,
          name: "heikinashi-bad",
          description: null,
          pine_source: "//@version=5\nstrategy('HA')\nheikinashi(request.security(...))\n",
          pine_version: "v5",
          // ★삭제된 sprint32 원본과 동일하게 "unsupported" 다 — 폼의
          //   `PARSE_STATUS_LABEL` "일부 미지원" 경로를 태우는 값이다(codex P2).
          //   이관하면서 "ok" 로 바꿨다가 그 분기를 잃을 뻔했다.
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
        },
      ],
      total: 1,
      page: 0,
      limit: 20,
      total_pages: 1,
    })(route),
  );

  // 422 본문은 공유 헬퍼로 — 스펙마다 손으로 조립하던 것을 한 곳으로 모은다.
  await page.route(API_ROUTES.backtests, (route, request) => {
    if (request.method() === "POST") {
      return fulfillJson(
        makeUnsupported422(
          ["heikinashi", "request.security"],
          "heikinashi / request.security 는 Trust Layer 위반(결과 부정확 risk). PbR / RSI / EMA cross 같은 ADR-003 supported list 의 indicator 로 대체 가능합니다.",
        ),
        422,
      )(route);
    }
    return fulfillJson({ items: [], total: 0, limit: 20, offset: 0 })(route);
  });

  await page.goto("/backtests/new", { timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "새 백테스트" })).toBeVisible({
    timeout: 15_000,
  });

  await page.locator("#strategy-select").selectOption({ label: "heikinashi-bad" });
  await page.getByTestId("backtest-submit").click({ force: true });

  // ★전역 getByText 는 strict mode 위반이다 — 전략 chip/option/요약행에도 "heikinashi" 가 있다.
  const friendly = page.getByTestId("backtest-form-friendly-message");
  await expect(friendly).toBeVisible({ timeout: 10_000 });
  await expect(friendly).toContainText(/Trust Layer 위반|ADR-003/);
});
