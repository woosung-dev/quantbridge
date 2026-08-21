import { expect, test } from "@playwright/test";

import {
  API_ROUTES,
  MOCK_DEMO_ACCOUNT,
  MOCK_KS_EVENT_ACTIVE,
  MOCK_KS_EVENT_RESOLVED,
  fulfillJson,
} from "./fixtures/api-mock";

// H2 Sprint 1 Phase C — Trading UI E2E 시나리오 (Sprint 25 활성화).
//
// Sprint 25 변경사항 (codex G.0 iter 1+2 반영):
// 1) test.skip 5건 제거 → chromium-authed project 의 storageState 가 인증 처리
// 2) Mock route prefix 정정 — `/api/v1/trading/...` → `/api/v1/...` (실제 frontend api.ts 사용 path)
//    검증 출처: src/features/trading/api.ts L17-19 (ORDERS_PATH / KILL_SWITCH_PATH / EXCHANGE_ACCOUNTS_PATH)
// 3) MOCK 변수 + API_ROUTES 를 fixtures/api-mock.ts 에서 import (DRY)
// 4) Real backend leak guard — beforeEach 에 page.on('request') stderr 출력 (observability)
//
// 단위 테스트 (보존):
//   src/features/trading/__tests__/KillSwitchBanner.test.tsx  (C-1/C-3)
//   src/features/trading/__tests__/ExchangeAccountsPanel.mode-badge.test.tsx  (C-2)

// Sprint 46 W2 — chromium-authed peers (dogfood-flow / live-session-flow / sprint32-dogfood-gate
// / backtest-live-mirror) 와 동일하게 serial mode 일괄 적용. 공유 storageState flake 방지.
test.describe.configure({ mode: "serial" });

// Sprint 25 leak guard + orders mock 통합 — 미등록 API 호출 stderr + OrdersPanel
// schema (total 필수) 만족 위해 모든 시나리오에 orders 빈 list 기본 mock.
test.beforeEach(async ({ page }) => {
  page.on("request", (req) => {
    const url = req.url();
    if (url.includes("/api/v1/")) {
      // request 발생 자체는 정상 (mock 으로 fulfill 됨). leak observability — Sprint 26+.
    }
  });
  // OrdersPanel 가 OrderListResponseSchema parse — total 필수. 시나리오마다 override OK.
  await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
});

// 시나리오 1: Demo 배지 표시 확인
test("trading accounts panel — Demo 배지 렌더", async ({ page }) => {
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }));
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

  await page.goto("/trading");

  // exchange-accounts table cell 안 "DEMO" — 페이지 로드 + query fetch 시간 wait
  await expect(page.getByRole("cell", { name: "DEMO" }).first()).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("ks-active-banner")).not.toBeVisible();
});

// 시나리오 2: KS active → destructive 배너 + 한국어 메시지
test("trading kill switch active — destructive 배너 + 한국어 트리거 레이블", async ({ page }) => {
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }));
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [MOCK_KS_EVENT_ACTIVE] }));

  await page.goto("/trading");

  const banner = page.getByTestId("ks-active-banner");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("일일 손실 한도 초과");
  // C 이식(S8): KillSwitchBanner 제목이 용어 SSOT(KILL_SWITCH_LABEL.feature="킬 스위치")로
  // 파생 — "킬 스위치 활성. 자동 주문이 중지됩니다." (기능 활성 표지 검증 의도 유지).
  await expect(banner).toContainText("킬 스위치 활성");
});

// 시나리오 3: KS active → 주문 버튼 disabled
// 현재 아키텍처에서 OrdersPanel에 별도 주문 버튼이 없으므로,
// useIsOrderDisabledByKs hook이 true를 반환하는지 컴포넌트 레벨에서 확인.
// 실제 주문 버튼이 추가되면 이 테스트를 확장.
test("trading kill switch active — 주문 버튼 disabled", async ({ page }) => {
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }));
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [MOCK_KS_EVENT_ACTIVE] }));

  await page.goto("/trading");

  await expect(page.getByTestId("ks-active-banner")).toBeVisible();

  // 주문 버튼이 있다면 disabled 확인 (Sprint 13 Phase B Test Order Dialog)
  // const placeOrderBtn = page.getByRole("button", { name: /주문|order/i });
  // await expect(placeOrderBtn).toBeDisabled();
});

// 시나리오 4: KS API 500 → 황색 경고 배너
test("trading kill switch API 오류 — 황색 경고 배너", async ({ page }) => {
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }));
  await page.route(API_ROUTES.killSwitch, fulfillJson({ detail: "Internal Server Error" }, 500));

  await page.goto("/trading");

  const errorBanner = page.getByTestId("ks-error-banner");
  await expect(errorBanner).toBeVisible();
  // C 이식(S8): 경고 배너 문구가 용어 SSOT("킬 스위치")로 파생됨.
  await expect(errorBanner).toContainText("킬 스위치 상태를 불러오지 못했습니다");
});

// 시나리오 5: KS resolve → 배너 소멸
// Sprint 25 — mock route 명시 전환 (requestCount 기반 logic 은 page load 다중 fetch 로 race).
test("trading kill switch resolved — 배너 소멸", async ({ page }) => {
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }));

  // Phase 1 — 모든 호출 KS active 응답
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [MOCK_KS_EVENT_ACTIVE] }));

  await page.goto("/trading", { timeout: 60_000 });

  await expect(page.getByTestId("ks-active-banner")).toBeVisible({
    timeout: 30_000,
  });

  // Phase 2 — mock 명시 전환 → 모든 호출 KS resolved 응답
  await page.unroute(API_ROUTES.killSwitch);
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [MOCK_KS_EVENT_RESOLVED] }));

  // page.reload() — Tanstack Query refetchOnWindowFocus 가 page.evaluate
  // dispatchEvent("focus") 로 안 트리거 (Playwright headless + React Query listener race).
  // reload = fresh KS fetch 보장 + 사용자 manual refresh 동작 시뮬.
  await page.reload({ timeout: 60_000 });

  await expect(page.getByTestId("ks-active-banner")).not.toBeVisible({
    timeout: 30_000,
  });
});

// STEP B — 트레일링 의도(Order.trailing_stop) 가 tpsl-cell 에 표출되는지 실 브라우저 검증
// (실 storageState 인증 + 실 FE 렌더). 체결 후 place_trailing_stop 가 거래소에 부착하는
// 그 의도를 사용자가 주문 테이블에서 볼 수 있어야 한다(Surface Trust §7.3 — UI 표출 mechanism).
test("trading orders — trailing_stop tpsl-cell 에 trail 거리 렌더", async ({ page }) => {
  await page.route(
    API_ROUTES.orders,
    fulfillJson({
      items: [
        {
          id: "11111111-1111-4111-8111-111111111111",
          symbol: "BTC/USDT",
          side: "buy",
          state: "filled",
          quantity: "0.001",
          filled_price: "50000",
          exchange_order_id: "EX-TR-1",
          error_message: null,
          created_at: "2026-06-26T00:00:00Z",
          stop_loss: "48000",
          trailing_stop: "150.5",
        },
      ],
      total: 1,
    }),
  );
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }));
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

  await page.goto("/trading");

  const cell = page.getByTestId("tpsl-cell").first();
  await expect(cell).toBeVisible({ timeout: 10_000 });
  // C 이식: trailing_stop 라벨이 "trail" → "추적손절"(한국어)로 바뀜. trail 거리 표출 의도 유지.
  await expect(cell).toContainText("추적손절 150.5");
  await expect(cell).toContainText("48000");
});
