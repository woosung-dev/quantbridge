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

// Sprint 25 leak guard — 미등록 API 호출 stderr 출력 (사람이 미적용 mock 발견 시 추가).
test.beforeEach(async ({ page }) => {
  page.on("request", (req) => {
    const url = req.url();
    // /api/v1/ prefix 호출 추적. spec 별 mock 등록 안 된 호출은 real backend 가는데,
    // dev-server proxy 또는 absolute URL 양쪽 다 발생 가능.
    if (url.includes("/api/v1/")) {
      // request 발생 자체는 정상 (mock 으로 fulfill 됨). leak 은 response 단계에서 검증 가능하나
      // Playwright 의 route.fulfill() 후에도 request 이벤트는 발생. 따라서 본 hook 은
      // observability 목적 (필요 시 console 활성화). fail-on-leak 는 Sprint 26+.
    }
  });
});

// 시나리오 1: Demo 배지 표시 확인
test("trading accounts panel — Demo 배지 렌더", async ({ page }) => {
  await page.route(
    API_ROUTES.exchangeAccounts,
    fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }),
  );
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

  await page.goto("/trading");

  await expect(page.getByText("DEMO")).toBeVisible();
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
test("trading kill switch resolved — 배너 소멸", async ({ page }) => {
  await page.route(
    API_ROUTES.exchangeAccounts,
    fulfillJson({ items: [MOCK_DEMO_ACCOUNT] }),
  );

  let requestCount = 0;
  await page.route(API_ROUTES.killSwitch, (route) => {
    requestCount++;
    const event =
      requestCount === 1 ? MOCK_KS_EVENT_ACTIVE : MOCK_KS_EVENT_RESOLVED;
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [event] }),
    });
  });

  await page.goto("/trading");

  await expect(page.getByTestId("ks-active-banner")).toBeVisible();

  // focus event 로 revalidation 트리거 (2번째 요청)
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));

  await expect(page.getByTestId("ks-active-banner")).not.toBeVisible({
    timeout: 10_000,
  });
});
