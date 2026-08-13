import { expect, test, type Page } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./fixtures/api-mock";
import {
  LONG_NOTIONAL,
  LONG_SD_NET,
  MOCK_EXCHANGE_ACCOUNT_LIST,
  MOCK_LIVE_SESSION_EVENTS,
  MOCK_LIVE_SESSION_LIST,
  MOCK_LIVE_SESSION_STATE,
  MOCK_OUTCOME_PARITY,
  MOCK_OUTCOME_PARITY_LONG_LEDGER_SUB,
  MOCK_STRATEGY_LIST,
  SESSION_ID,
} from "./fixtures/outcome-parity";

// BL-608 — outcome-parity 패널 e2e 안전망 (그전까지 `frontend/e2e/**` 에 이 문자열 0건).
//
// ★로케이터는 **data-testid 와 값(title 문자열)만** 쓴다 (BL-597 규약). 상세가 열린
// `/trading` 에는 `<table>` 이 5개 있고 「산출 불가」 는 페이지에서 11회 매치된다
// (2026-08-06 qa 프로브 실측) — 느슨한 role/text 로케이터는 스코프끼리도 헷갈린다.
// 스코프는 `outcome-parity-{session,strategy}-*` 접두로 가르고, 정체성은
// `live-session-detail-<uuid>` 로 못 박는다. 원문 보존 검증도 구조 셀렉터(`[title]`)가
// 아니라 `getByTitle(원문)` 으로 — 값으로 찾으면 DOM 모양이 바뀌어도 재는 대상이 안 바뀐다.
//
// ★응답 본문은 `fixtures/outcome-parity.ts` 가 SSOT 다. 그 파일은 playwright 를 import 하지
// 않아 vitest 가 같은 객체를 실제 Zod 스키마에 대입한다(`outcome-parity-e2e-fixtures.test.ts`).
// mock 이 계약과 어긋나면 e2e 가 아니라 **그 단위테스트**가 먼저 빨개진다.

test.describe.configure({ mode: "serial" });

// ★상세 하위 경로를 **먼저** 등록한다. 뒤에 등록한 catch-all 이 우선 매치되고
// `route.fallback()` 으로 여기로 넘어온다 (live-session-flow.spec.ts 와 같은 패턴).
async function mockTradingPage(page: Page, parity: unknown = MOCK_OUTCOME_PARITY) {
  await page.route(API_ROUTES.strategies, fulfillJson(MOCK_STRATEGY_LIST));
  await page.route(API_ROUTES.exchangeAccounts, fulfillJson(MOCK_EXCHANGE_ACCOUNT_LIST));
  await page.route(API_ROUTES.orders, fulfillJson({ items: [], total: 0 }));
  await page.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));

  await page.route(
    `**/api/v1/live-sessions/${SESSION_ID}/state**`,
    fulfillJson(MOCK_LIVE_SESSION_STATE),
  );
  await page.route(
    `**/api/v1/live-sessions/${SESSION_ID}/events**`,
    fulfillJson(MOCK_LIVE_SESSION_EVENTS),
  );
  await page.route(
    `**/api/v1/live-sessions/${SESSION_ID}/alert-rules**`,
    fulfillJson({ items: [], total: 0 }),
  );
  await page.route(
    `**/api/v1/live-sessions/${SESSION_ID}/outcome-parity**`,
    fulfillJson(parity),
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
    return fulfillJson(MOCK_LIVE_SESSION_LIST)(route);
  });
}

async function openSessionDetail(page: Page, parity: unknown = MOCK_OUTCOME_PARITY) {
  await mockTradingPage(page, parity);
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
    // 옆 카드 안내는 **비단정**이어야 한다 — 늦은 체결이 인접 세션 창으로 잡히면 이 세션
    // 이벤트의 청산이 전략 축에 포함될 수 있다(backend `order_repository` 창 계약).
    await expect(banner).toContainText("포함할 수 있습니다");
    await expect(banner).not.toContainText("한 건도");

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
    await expect(sd.getByTitle(LONG_SD_NET)).toBeVisible();

    const notional = page.getByTestId("outcome-parity-strategy-round-trip-notional");
    await expect(notional).toHaveText("153223.9543");
    await expect(notional.getByTitle(LONG_NOTIONAL)).toBeVisible();

    // 폭도 직접 잰다 — 텍스트 단언만으로는 "화면에서 잘리는가" 를 못 잰다.
    // qa 실측 원문 렌더는 scrollWidth **551px**(clientWidth 66px, 8.3배)였다. 150px 상한은
    // 폰트·DPI 가 달라져도 원문 복귀를 반드시 잡고, 반올림된 6자리는 여유롭게 통과한다.
    const scrollWidth = await sd.evaluate((el) => el.scrollWidth);
    expect(scrollWidth).toBeLessThan(150);
  });

  // BL-548 — 375px 에서 이 패널이 문서 전체에 가로 스크롤을 낳는다.
  //
  // ★**실측 픽스처로는 이 결함이 안 보인다.** 2026-08-09 재현 결과 `MOCK_OUTCOME_PARITY`
  // 위에서는 수리 전에도 오버플로가 0 이었다 — 그 응답의 `sub` 전용 네 필드가 마침
  // `"0"`·`"20"` 으로 짧아서다. BL 이 적은 24px 은 BL-607(값 타일 반올림, 2026-08-06)이
  // 이미 지웠다. 남은 경로는 **반올림을 안 거치는 `sub` 캡션**이고, 그 자리에 같은 원장이
  // 주는 51자리 Decimal 이 들어오면 다시 넘친다(수리 전 191px).
  //
  // 그래서 판별력 있는 픽스처로 잰다. 인과 분리도 실측했다 —
  // 상세 닫힘 **0** / 열림 **191** / 열림 + 패널 `display:none` **0**.
  test("375px — 원장 Decimal 이 sub 로 와도 문서 가로 오버플로가 0이다", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await openSessionDetail(page, MOCK_OUTCOME_PARITY_LONG_LEDGER_SUB);

    const overflow = await page.evaluate(
      () => document.body.scrollWidth - document.body.clientWidth,
    );
    expect(overflow).toBe(0);
  });
});
