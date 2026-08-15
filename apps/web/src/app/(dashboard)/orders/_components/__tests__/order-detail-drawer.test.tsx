// 주문 상세 드로어 — 손익 **출처**가 말로 적히는지 본다 ([BL-458], 2026-08-16).
// 종전 드로어는 「손익 확정 시각」의 빈칸 여부로 사용자가 추정/확정을 추론하게 두었다.
// 같은 판정을 목록은 `ORDER_REALIZED_PNL_SOURCE_LABEL` 로 말하고 상세만 침묵한 것이라,
// `realizedPnlSource` 주석이 경고한 「화면끼리 각자 계산」의 세 번째 판이었다.
//
// ★음성 대조를 함께 둔다 — 손익을 안 보여주는 주문에는 출처도 **적지 않아야** 한다.
// 그 케이스가 없으면 「전부 「추정」이라고 적는다」는 구현이 초록으로 통과한다.

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { OrderDetailDrawer } from "@/app/(dashboard)/orders/_components/order-detail-drawer";
import {
  ORDER_CSV_EXTRA_HEADER,
  ORDER_REALIZED_PNL_SOURCE_LABEL,
} from "@/features/trading/labels";
import { EMPTY_CELL } from "@/lib/labels";
import type { Order } from "@/features/trading/schemas";

function makeOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    strategy_id: "00000000-0000-4000-8000-000000000111",
    exchange_account_id: "00000000-0000-4000-8000-000000000222",
    symbol: "BTC/USDT",
    side: "buy",
    type: "market",
    price: null,
    state: "filled",
    quantity: "0.021",
    idempotency_key: "order-0001",
    filled_price: "62880.00",
    exchange_order_id: "78409188",
    error_message: null,
    submitted_at: "2026-04-14T20:00:01Z",
    filled_at: "2026-04-14T20:00:04Z",
    created_at: "2026-04-14T20:00:04Z",
    leverage: 5,
    margin_mode: "isolated",
    reduce_only: false,
    trigger_price: null,
    trigger_by: null,
    take_profit: null,
    stop_loss: null,
    trigger_direction: null,
    oco_group_id: null,
    trailing_stop: null,
    filled_quantity: null,
    realized_pnl: null,
    realized_pnl_synced_at: null,
    ...overrides,
  };
}

/** 「손익 출처」 행의 값 셀 텍스트. 라벨 옆 값만 집는다. */
function sourceCellText(): string | null {
  const label = screen.getByText(ORDER_CSV_EXTRA_HEADER.realizedPnlSource);
  return label.parentElement?.textContent?.replace(
    ORDER_CSV_EXTRA_HEADER.realizedPnlSource,
    "",
  ) ?? null;
}

describe("OrderDetailDrawer — 실현 손익 출처", () => {
  afterEach(cleanup);

  it("거래소 확정 손익이면 출처를 「거래소 확정」으로 적는다", () => {
    render(
      <OrderDetailDrawer
        order={makeOrder({
          realized_pnl: "12.34",
          realized_pnl_synced_at: "2026-04-14T20:00:05Z",
        })}
        open
        onOpenChange={() => {}}
      />,
    );
    expect(sourceCellText()).toContain(ORDER_REALIZED_PNL_SOURCE_LABEL.confirmed);
  });

  it("아직 스윕이 안 온 손익이면 출처를 「추정」으로 적는다", () => {
    render(
      <OrderDetailDrawer
        order={makeOrder({ realized_pnl: "12.34", realized_pnl_synced_at: null })}
        open
        onOpenChange={() => {}}
      />,
    );
    expect(sourceCellText()).toContain(ORDER_REALIZED_PNL_SOURCE_LABEL.estimated);
  });

  it("★손익을 안 보여주는 주문에는 출처도 적지 않는다 (없는 숫자에 등급을 매기지 않는다)", () => {
    // rejected 는 `displayRealizedPnl` 이 null 을 내는 경로다 — 남아 있는 pine_v2 추정치가
    // 확정 손실처럼 보이는 것을 막으려 목록이 이미 그렇게 정해 뒀다.
    render(
      <OrderDetailDrawer
        order={makeOrder({
          state: "rejected",
          realized_pnl: "-5.00",
          realized_pnl_synced_at: null,
        })}
        open
        onOpenChange={() => {}}
      />,
    );
    const text = sourceCellText();
    expect(text).toContain(EMPTY_CELL);
    expect(text).not.toContain(ORDER_REALIZED_PNL_SOURCE_LABEL.estimated);
  });
});
