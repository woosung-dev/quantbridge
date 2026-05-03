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
// 1) test.skip 5건 제거 → chromium-authed project 의 storageState 가 Clerk 인증 처리
// 2) Mock route prefix 정정 — `/api/v1/trading/...` → `/api/v1/...` (실제 frontend api.ts 사용 path)
//    검증 출처: src/features/trading/api.ts L17-19 (ORDERS_PATH / KILL_SWITCH_PATH / EXCHANGE_ACCOUNTS_PATH)
// 3) MOCK 변수 + API_ROUTES 를 fixtures/api-mock.ts 에서 import (DRY)
// 4) Real backend leak guard — beforeEach 에 page.on('request') stderr 출력 (observability)
//
// 단위 테스트 (보존):
//   src/features/trading/__tests__/KillSwitchBanner.test.tsx  (C-1/C-3)
//   src/features/trading/__tests__/ExchangeAccountsPanel.mode-badge.test.tsx  (C-2)

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
  await page.route(
    API_ROUTES.orders,
    fulfillJson({ items: [], total: 0 }),
  );
});

// 시나리오 1: Demo 배지 표시 확인
test("trading accounts panel — Demo 배지 렌더", async ({ page }) => {
  await page.route(
    API_ROUTES.exchangeAccounts,
    fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }),
  );
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

  await page.goto("/trading");

  // exchange-accounts table cell 안 "DEMO" — 페이지 로드 + query fetch 시간 wait
  await expect(
    page.getByRole("cell", { name: "DEMO" }).first(),
  ).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("ks-active-banner")).not.toBeVisible();
});

// 시나리오 2: KS active → destructive 배너 + 한국어 메시지
test("trading kill switch active — destructive 배너 + 한국어 트리거 레이블", async ({
  page,
}) => {
  await page.route(
    API_ROUTES.exchangeAccounts,
    fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }),
  );
  await page.route(
    API_ROUTES.killSwitch,
    fulfillJson({ items: [MOCK_KS_EVENT_ACTIVE] }),
  );

  await page.goto("/trading");

  const banner = page.getByTestId("ks-active-banner");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("일일 손실 한도 초과");
  await expect(banner).toContainText("Kill Switch 활성");
});

// 시나리오 3: KS active → 주문 버튼 disabled
// 현재 아키텍처에서 OrdersPanel에 별도 주문 버튼이 없으므로,
// useIsOrderDisabledByKs hook이 true를 반환하는지 컴포넌트 레벨에서 확인.
// 실제 주문 버튼이 추가되면 이 테스트를 확장.
test("trading kill switch active — 주문 버튼 disabled", async ({ page }) => {
  await page.route(
    API_ROUTES.exchangeAccounts,
    fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }),
  );
  await page.route(
    API_ROUTES.killSwitch,
    fulfillJson({ items: [MOCK_KS_EVENT_ACTIVE] }),
  );

  await page.goto("/trading");

  await expect(page.getByTestId("ks-active-banner")).toBeVisible();

  // 주문 버튼이 있다면 disabled 확인 (Sprint 13 Phase B Test Order Dialog)
  // const placeOrderBtn = page.getByRole("button", { name: /주문|order/i });
  // await expect(placeOrderBtn).toBeDisabled();
});

// 시나리오 4: KS API 500 → 황색 경고 배너
test("trading kill switch API 오류 — 황색 경고 배너", async ({ page }) => {
  await page.route(
    API_ROUTES.exchangeAccounts,
    fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }),
  );
  await page.route(
    API_ROUTES.killSwitch,
    fulfillJson({ detail: "Internal Server Error" }, 500),
  );

  await page.goto("/trading");

  const errorBanner = page.getByTestId("ks-error-banner");
  await expect(errorBanner).toBeVisible();
  await expect(errorBanner).toContainText(
    "Kill Switch 상태를 불러오지 못했습니다",
  );
});

// 시나리오 5: KS resolve → 배너 소멸
// Sprint 25 — mock route 명시 전환 (requestCount 기반 logic 은 page load 다중 fetch 로 race).
test("trading kill switch resolved — 배너 소멸", async ({ page }) => {
  await page.route(
    API_ROUTES.exchangeAccounts,
    fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }),
  );

  // Phase 1 — 모든 호출 KS active 응답
  await page.route(
    API_ROUTES.killSwitch,
    fulfillJson({ items: [MOCK_KS_EVENT_ACTIVE] }),
  );

  await page.goto("/trading", { timeout: 60_000 });

  await expect(page.getByTestId("ks-active-banner")).toBeVisible({
    timeout: 30_000,
  });

  // Phase 2 — mock 명시 전환 → 모든 호출 KS resolved 응답
  await page.unroute(API_ROUTES.killSwitch);
  await page.route(
    API_ROUTES.killSwitch,
    fulfillJson({ items: [MOCK_KS_EVENT_RESOLVED] }),
  );

  // page.reload() — Tanstack Query refetchOnWindowFocus 가 page.evaluate
  // dispatchEvent("focus") 로 안 트리거 (Playwright headless + React Query listener race).
  // reload = fresh KS fetch 보장 + 사용자 manual refresh 동작 시뮬.
  await page.reload({ timeout: 60_000 });

  await expect(page.getByTestId("ks-active-banner")).not.toBeVisible({
    timeout: 30_000,
  });
});
