// [BL-766] 행 로케이터 음성 대조 — `tr` + `.first()` 가 **헤더 행을 집는다**를 고정한다.
//
// ★이 항목의 핵심은 수리가 아니라 **판별력**이다. `page.locator("tr", { hasText })` 는
//   `<thead>` 의 헤더 행도 후보로 잡고, DOM 순서상 헤더가 먼저이므로 `.first()` 가
//   **헤더를 집는다.** 그러면 그 뒤의 `toHaveCount(0)` 류 단언은 데이터와 무관하게
//   통과한다 — 초록이 「그 화면이 동작한다」를 말하지 않는다.
//
// ★**초판은 「표를 비우고 red 인지 본다」였고 그것이 틀렸다**(2026-08-16 실측):
//   주문이 0건이면 이 화면은 표 대신 빈 상태 UI 를 그려서 **헤더째 사라진다.**
//   그러면 위험한 패턴도 안전한 패턴도 똑같이 0 이라 **두 단언이 판별력 없이 통과**한다.
//   그 사실을 잡은 것은 초판이 앞에 둔 「표가 렌더됐는가」 전제 확인 한 줄이었다.
//   ⇒ 대조는 **데이터가 있는 상태**에서 세운다.

import { expect, test } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./fixtures/api-mock";

const FILLED_ID = "d0000000-0000-4000-8000-0000000009f3";

const ORDER_FILLED = {
  id: FILLED_ID,
  symbol: "BTC/USDT",
  side: "buy",
  state: "filled",
  quantity: "0.01",
  filled_price: "50000",
  exchange_order_id: "ex-1",
  error_message: null,
  created_at: "2026-07-23T01:00:00+00:00",
  reduce_only: false,
  trigger_price: null,
  trigger_by: null,
  take_profit: null,
  stop_loss: null,
  trigger_direction: null,
  oco_group_id: null,
  trailing_stop: null,
};

test.describe("[BL-766] 표 행 로케이터 음성 대조", () => {
  test("`tr` 의 .first() 는 헤더 행이고 `tbody tr` 의 .first() 는 데이터 행이다", async ({
    page,
  }) => {
    const context = page.context();
    await context.route(
      API_ROUTES.strategies,
      fulfillJson({ items: [], total: 0, page: 1, limit: 20, total_pages: 1 }),
    );
    await context.route(API_ROUTES.backtests, fulfillJson({ items: [], total: 0 }));
    await context.route(API_ROUTES.exchangeAccounts, fulfillJson({ items: [] }));
    await context.route(API_ROUTES.killSwitch, fulfillJson({ items: [] }));
    await context.route(API_ROUTES.liveSessions, fulfillJson({ items: [], total: 0 }));
    await context.route(API_ROUTES.orders, fulfillJson({ items: [ORDER_FILLED], total: 1 }));

    await page.goto("/orders");

    // 전제 — 표가 실제로 렌더됐는가. 이 줄이 없으면 아래 두 단언이 둘 다
    // 「없어서 0」으로 조용히 통과한다(초판이 정확히 그렇게 실패했다).
    await expect(page.locator("thead th").first()).toBeVisible();
    await expect(page.locator("tbody tr").first()).toBeVisible();

    // ⑴ ★위험한 패턴 — 헤더에 「체결가」·「체결수량」 열이 있어 `hasText: "체결"` 이 매치되고
    //    `.first()` 가 **헤더**를 집는다. 이 단언이 이 파일의 존재 이유다.
    const unsafeFirst = page.locator("tr", { hasText: "체결" }).first();
    const unsafeIsHeader = await unsafeFirst.evaluate((el) => el.closest("thead") !== null);
    expect(
      unsafeIsHeader,
      "`tr` + .first() 가 헤더를 집지 않는다 — 헤더 문구가 바뀌었을 수 있다. " +
        "그렇다면 이 가드가 지키던 위험이 아직 있는지 다시 판단해라.",
    ).toBe(true);

    // ⑵ 그 헤더 행에는 클릭 핸들러도 버튼도 없다 — **이것이 거짓 초록의 정체다.**
    //    아래 단언이 통과하는 것 자체는 수리가 아니라 **증상**이다.
    await expect(unsafeFirst.getByRole("button", { name: "주문 취소" })).toHaveCount(0);

    // ⑶ 안전한 패턴 — 우리가 옮겨 간 형태가 실제로 데이터 행을 집는가.
    const safeFirst = page.locator("tbody tr").filter({ hasText: "체결" }).first();
    const safeIsBody = await safeFirst.evaluate((el) => el.closest("tbody") !== null);
    expect(safeIsBody).toBe(true);
    await expect(safeFirst).toContainText("BTC/USDT");
  });
});
