import { expect, test } from "@playwright/test";

// H2 Sprint 1 Phase C — Trading UI E2E 시나리오.
//
// 주의: /trading 페이지는 Clerk 인증 후에만 접근 가능하며,
// CI 환경에서는 Clerk Dev key와 인증 fixture가 없어 실제 페이지를 렌더할 수 없음.
// 따라서 모든 시나리오를 test.skip으로 마킹하고, 인증 fixture 추가 시 활성화할 수 있도록
// 완전한 구현체를 보존.
//
// 활성화 조건:
// 1) e2e/fixtures/auth.ts 에서 Clerk signed-in state를 storageState로 제공
// 2) PLAYWRIGHT_BASE_URL 환경변수로 인증된 세션을 가진 개발 서버 포인팅
//
// 대체 단위 테스트:
//   frontend/src/features/trading/__tests__/KillSwitchBanner.test.tsx  (C-1/C-3)
//   frontend/src/features/trading/__tests__/ExchangeAccountsPanel.mode-badge.test.tsx  (C-2)

// Mock 객체는 완전 정의 (... 생략 금지)
const MOCK_DEMO_ACCOUNT = {
  id: "a0000000-0000-4000-a000-000000000001",
  name: "Bybit Demo",
  exchange: "bybit_futures",
  mode: "demo",
  label: "Bybit Demo",
  api_key_masked: "***masked***",
  is_active: true,
  created_at: "2026-04-24T00:00:00Z",
};

const MOCK_KS_EVENT_ACTIVE = {
  id: "b0000000-0000-4000-b000-000000000001",
  trigger_type: "daily_loss",
  trigger_value: "600.00",
  threshold: "500.00",
  triggered_at: "2026-04-24T10:00:00Z",
  resolved_at: null,
};

const MOCK_KS_EVENT_RESOLVED = {
  id: "b0000000-0000-4000-b000-000000000001",
  trigger_type: "daily_loss",
  trigger_value: "600.00",
  threshold: "500.00",
  triggered_at: "2026-04-24T10:00:00Z",
  resolved_at: "2026-04-24T11:00:00Z",
};

// 시나리오 1: Demo 배지 표시 확인
test.skip("trading accounts panel — Demo 배지 렌더", async ({ page }) => {
  // Exchange Accounts API mock
  await page.route("**/api/v1/trading/exchange-accounts*", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [MOCK_DEMO_ACCOUNT] }),
    });
  });

  // KS API mock (정상, 비활성)
  await page.route("**/api/v1/trading/kill-switch*", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [] }),
    });
  });

  await page.goto("/trading");

  // DEMO 배지가 보임
  await expect(page.getByText("DEMO")).toBeVisible();
  // destructive 배너는 없음
  await expect(page.getByTestId("ks-active-banner")).not.toBeVisible();
});

// 시나리오 2: KS active → destructive 배너 + 한국어 메시지
test.skip("trading kill switch active — destructive 배너 + 한국어 트리거 레이블", async ({
  page,
}) => {
  await page.route("**/api/v1/trading/kill-switch*", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [MOCK_KS_EVENT_ACTIVE] }),
    });
  });

  await page.goto("/trading");

  // destructive 배너 노출
  const banner = page.getByTestId("ks-active-banner");
  await expect(banner).toBeVisible();

  // 한국어 레이블 확인
  await expect(banner).toContainText("일일 손실 한도 초과");
  await expect(banner).toContainText("Kill Switch 활성");
});

// 시나리오 3: KS active → 주문 버튼 disabled
// 현재 아키텍처에서 OrdersPanel에 별도 주문 버튼이 없으므로,
// useIsOrderDisabledByKs hook이 true를 반환하는지 컴포넌트 레벨에서 확인.
// 실제 주문 버튼이 추가되면 이 테스트를 확장.
test.skip("trading kill switch active — 주문 버튼 disabled", async ({ page }) => {
  await page.route("**/api/v1/trading/kill-switch*", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [MOCK_KS_EVENT_ACTIVE] }),
    });
  });

  await page.goto("/trading");

  // KS 배너가 보임 → KS active 상태 확인
  await expect(page.getByTestId("ks-active-banner")).toBeVisible();

  // 주문 버튼이 있다면 disabled 확인 (버튼 추가 후 활성화)
  // const placeOrderBtn = page.getByRole("button", { name: /주문|order/i });
  // await expect(placeOrderBtn).toBeDisabled();
});

// 시나리오 4: KS API 500 → 황색 경고 배너
test.skip("trading kill switch API 오류 — 황색 경고 배너", async ({ page }) => {
  await page.route("**/api/v1/trading/kill-switch*", (route) => {
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Internal Server Error" }),
    });
  });

  await page.goto("/trading");

  // 황색 경고 배너 노출
  const errorBanner = page.getByTestId("ks-error-banner");
  await expect(errorBanner).toBeVisible();
  await expect(errorBanner).toContainText("Kill Switch 상태를 불러오지 못했습니다");
});

// 시나리오 5: KS resolve → 배너 소멸
test.skip("trading kill switch resolved — 배너 소멸", async ({ page }) => {
  let requestCount = 0;

  // 첫 번째 호출은 active, 두 번째 호출은 resolved
  await page.route("**/api/v1/trading/kill-switch*", (route) => {
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

  // 초기 — destructive 배너 노출
  await expect(page.getByTestId("ks-active-banner")).toBeVisible();

  // focus event로 revalidation 트리거 (2번째 요청)
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));

  // 배너 소멸 대기
  await expect(page.getByTestId("ks-active-banner")).not.toBeVisible({
    timeout: 10_000,
  });
});
