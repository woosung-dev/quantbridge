// 청산 잔량이 **화면에** 보이는지 실브라우저로 판정한다.
//
// ★왜 라우트를 스텁하는가. 잔여 미체결 진입은 거래소 상태라 로컬 DB 로 만들 수 없고,
//   만들 수 있다 해도 세 상태(잔량 있음 / 잔량 없음 / 확인 실패)를 마음대로 오갈 수 없다.
//   여기서 재려는 것은 거래소 배선이 아니라 **응답이 화면에 도달하는가** 이므로, 응답을
//   고정하고 Zod 파싱 · React Query · 렌더까지 진짜로 돌린다. 거래소 축은 백엔드 시험이 잰다.
//
// ★핵심 판정은 세 번째다 — 빈 목록이 「잔량 없음」과 「거래소에 못 물어봤다」를 구분하지
//   못하는 것이 이 결함 계열의 본체다. 두 testid 가 서로를 배제하는지 양방향으로 본다.
import { expect, test, type Page } from "@playwright/test";

import { fulfillJson } from "./fixtures/api-mock";

// ★`mode: "serial"` 을 쓰지 않는다. `chromium-authed` 는 config 가 이미
//   `fullyParallel: false` + `--workers=1` 로 순차 실행을 보장하는데, serial 을 더 얹으면
//   앞 시험이 깨질 때 **뒤가 skip 된다.** 이 파일의 뒤쪽 절반이 음성 대조라 그 순간
//   「구분이 되는가」라는 판정 자체가 사라진다.

const ACCOUNT_ID ="a0000000-0000-4000-a000-0000000000c1";
const SESSION_ID = "c0000000-0000-4000-8000-0000000000c1";
const SYMBOL = "BTC/USDT";

const ACCOUNT = {
  id: ACCOUNT_ID,
  exchange: "bybit_futures",
  mode: "demo",
  label: "Bybit Demo",
  api_key_masked: "***masked***",
  exchange_uid: "558689281",
  read_only: false,
  created_at: "2026-08-10T00:00:00Z",
};

const ACCOUNT_POSITIONS = {
  account_id: ACCOUNT_ID,
  supported: true,
  reason: null,
  fetched_at: "2026-08-10T04:00:00Z",
  settle_coin: "USDT",
  truncated: false,
  rows: [
    {
      symbol: SYMBOL,
      position: {
        side: "short",
        size: "0.029",
        entry_price: "65340.2",
        mark_price: "65100",
        unrealized_pnl: "7.22",
        take_profit_prices: [],
        stop_loss_prices: [],
        has_trailing_stop: false,
        liquidation_price: null,
        leverage: "10",
      },
      closable_session_id: SESSION_ID,
      close_blocked_reason: null,
    },
  ],
};

/** 서버 실측 그대로 — `qty`·`trigger_price` 는 와이어에서 문자열이다. */
const RESTING_ORDERS = [
  {
    order_id: "1a2b3c4d-5e6f",
    side: "buy",
    qty: "0.029",
    trigger_price: "64000",
    order_link_id: "qb-entry-1",
  },
  {
    order_id: "9f8e7d6c-5b4a",
    side: "buy",
    qty: "0.010",
    trigger_price: "63500",
    order_link_id: null,
  },
];

const CLOSE_ROUTE = "**/api/v1/live-sessions/*/positions/close**";

/**
 * 청산 흐름을 세워 놓고 확인창의 청산 버튼까지 누른다.
 *
 * ★라우트 등록 순서가 계약이다. playwright 는 **나중에 등록한 핸들러**를 쓰므로
 * 넓은 `live-sessions` 패턴을 먼저 깔고 청산 경로를 그 뒤에 깐다. 뒤집으면 청산 요청이
 * 세션 목록 응답을 받는다.
 */
async function openCloseDialog(page: Page, close: { status: number; body: unknown }) {
  await page.route("**/api/v1/live-sessions**", fulfillJson({ items: [], total: 0 }));
  await page.route("**/api/v1/exchange-accounts**", fulfillJson({ items: [ACCOUNT] }));
  await page.route(`**/api/v1/exchange-accounts/${ACCOUNT_ID}/positions**`, fulfillJson(ACCOUNT_POSITIONS));
  await page.route(CLOSE_ROUTE, fulfillJson(close.body, close.status));

  await page.goto("/trading", { timeout: 60_000 });
  await page.getByTestId(`account-position-close-${SYMBOL}`).click();
  await page.getByRole("button", { name: "청산 실행" }).click();
}

test("409 잔량 — 청산을 내지 않았고 남은 진입 주문을 목록으로 보여준다", async ({ page }) => {
  await openCloseDialog(page, {
    status: 409,
    body: {
      detail: {
        code: "resting_conditional_entries",
        count: RESTING_ORDERS.length,
        detail: "포지션은 없지만 미체결 진입 주문 2건이 남아 있습니다.",
        orders: RESTING_ORDERS,
      },
    },
  });

  const panel = page.getByTestId("close-outcome-blocked");
  await expect(panel).toBeVisible();
  await expect(panel).toContainText("포지션은 없지만 미체결 진입 주문 2건이 남아 있습니다.");

  // ★종전에는 여기에 `API 409 /api/v1/…` 만 떴다.
  await expect(panel).not.toContainText("API 409");

  const entries = page.getByTestId("close-resting-entry");
  await expect(entries).toHaveCount(2);
  await expect(entries.first()).toContainText("1a2b3c4d-5e6f");
  await expect(entries.first()).toContainText("64000");
  await expect(entries.first()).toContainText("qb-entry-1");
  // `order_link_id` 가 없으면 CLI 와 같은 자리표시자를 쓴다.
  await expect(entries.nth(1)).toContainText("link -");

  // 주문을 내지 않았으므로 재시도가 유효하다.
  await expect(page.getByRole("button", { name: "청산 실행" })).toBeVisible();
});

test("409 잔량 0건 — 음성 대조. 목록 자체가 뜨지 않는다", async ({ page }) => {
  await openCloseDialog(page, {
    status: 409,
    body: {
      detail: {
        code: "resting_conditional_entries",
        count: 0,
        detail: "포지션은 없지만 미체결 진입 주문 0건이 남아 있습니다.",
        orders: [],
      },
    },
  });

  await expect(page.getByTestId("close-outcome-blocked")).toBeVisible();
  await expect(page.getByTestId("close-resting-list")).toHaveCount(0);
  await expect(page.getByTestId("close-resting-entry")).toHaveCount(0);
});

test("202 접수 + 잔량 — 접수를 말하고 남은 주문도 말한다", async ({ page }) => {
  await openCloseDialog(page, {
    status: 202,
    body: {
      order_id: "d0000000-0000-4000-8000-0000000000c1",
      state: "submitted",
      detail: "reduce-only market close accepted · 미체결 진입 주문 2건이 남아 있다",
      resting_entries: RESTING_ORDERS,
      resting_entries_unknown: false,
    },
  });

  const panel = page.getByTestId("close-outcome-resting");
  await expect(panel).toBeVisible();
  await expect(panel).toContainText("미체결 진입 주문 2건이 남아 있습니다.");
  await expect(page.getByTestId("close-resting-entry")).toHaveCount(2);

  // 원장 안내는 경고보다 **먼저** 온다 (CLI 와 같은 순서).
  await expect(page.getByTestId("close-ledger-note")).toBeVisible();

  // 주문은 이미 나갔다 — 재제출 경로가 없어야 한다.
  await expect(page.getByRole("button", { name: "청산 실행" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "확인" })).toBeVisible();

  // ★양방향 배제 — 미확인 상태와 같은 화면이 아니다.
  await expect(page.getByTestId("close-outcome-unknown")).toHaveCount(0);
});

test("202 접수 + 잔량 미확인 — 잔량 있음과도, 잔량 없음과도 다르게 보인다", async ({ page }) => {
  await openCloseDialog(page, {
    status: 202,
    body: {
      order_id: "d0000000-0000-4000-8000-0000000000c2",
      state: "submitted",
      detail: "reduce-only market close accepted · 미체결 진입 주문 확인 실패",
      resting_entries: [],
      resting_entries_unknown: true,
    },
  });

  const panel = page.getByTestId("close-outcome-unknown");
  await expect(panel).toBeVisible();
  await expect(panel).toContainText("확인하지 못했습니다");
  await expect(panel).toContainText("잔량이 없다는 뜻이 아니므로");

  // ★핵심 판정. 빈 목록을 「잔량 없음」으로도, 「잔량 있음」으로도 그리지 않는다.
  await expect(page.getByTestId("close-outcome-resting")).toHaveCount(0);
  await expect(page.getByTestId("close-resting-entry")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "청산 실행" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "확인" })).toBeVisible();
});

test("202 접수 + 잔량 없음 — 확인창이 조용히 닫힌다", async ({ page }) => {
  await openCloseDialog(page, {
    status: 202,
    body: {
      order_id: "d0000000-0000-4000-8000-0000000000c3",
      state: "submitted",
      detail: "reduce-only market close accepted",
      resting_entries: [],
      resting_entries_unknown: false,
    },
  });

  // ★양성 대조 — 위 셋이 뜨는 것이 「패널이 항상 뜬다」가 아님을 보인다.
  await expect(page.getByRole("button", { name: "청산 실행" })).toHaveCount(0);
  await expect(page.getByTestId("close-outcome-resting")).toHaveCount(0);
  await expect(page.getByTestId("close-outcome-unknown")).toHaveCount(0);
  await expect(page.getByTestId("close-outcome-blocked")).toHaveCount(0);
  await expect(page.getByTestId("close-outcome-failed")).toHaveCount(0);
});
