// OrderSchema Wave1 TP/SL 필드 1:1 검증 — BE OrderResponse 와 정합.

import { describe, expect, it } from "vitest";

import { OrderSchema } from "../schemas";

const BASE = {
  id: "a0000000-0000-4000-a000-000000000001",
  strategy_id: "a0000000-0000-4000-a000-000000000002",
  exchange_account_id: "a0000000-0000-4000-a000-000000000003",
  symbol: "BTCUSDT",
  side: "buy" as const,
  type: "limit" as const,
  price: "50000",
  state: "filled" as const,
  quantity: "0.01",
  idempotency_key: "idempotency-1",
  filled_price: "50000",
  exchange_order_id: "broker-1",
  error_message: null,
  submitted_at: "2026-06-26T10:00:01Z",
  filled_at: "2026-06-26T10:00:02Z",
  created_at: "2026-06-26T10:00:00Z",
  leverage: 5,
  margin_mode: "isolated" as const,
};

describe("OrderSchema detail fields", () => {
  it("목록 응답에 이미 포함된 상세 필드를 빠짐없이 parse 한다", () => {
    const parsed = OrderSchema.parse(BASE);
    expect(parsed).toMatchObject({
      strategy_id: BASE.strategy_id,
      exchange_account_id: BASE.exchange_account_id,
      type: "limit",
      price: "50000",
      idempotency_key: "idempotency-1",
      submitted_at: "2026-06-26T10:00:01Z",
      filled_at: "2026-06-26T10:00:02Z",
      leverage: 5,
      margin_mode: "isolated",
    });
  });
});

describe("OrderSchema Wave1 fields", () => {
  it("Wave1 필드 포함 응답을 parse 한다 (Decimal→string)", () => {
    const parsed = OrderSchema.parse({
      ...BASE,
      reduce_only: true,
      trigger_price: "49000",
      trigger_by: "MarkPrice",
      take_profit: "55000",
      stop_loss: "48000",
    });
    expect(parsed.reduce_only).toBe(true);
    expect(parsed.trigger_price).toBe("49000");
    expect(parsed.trigger_by).toBe("MarkPrice");
    expect(parsed.take_profit).toBe("55000");
    expect(parsed.stop_loss).toBe("48000");
  });

  it("Wave1 필드 누락 fixture 도 graceful 하게 parse 한다 (default)", () => {
    const parsed = OrderSchema.parse(BASE);
    expect(parsed.reduce_only).toBe(false);
    expect(parsed.trigger_price).toBeNull();
    expect(parsed.trigger_by).toBeNull();
    expect(parsed.take_profit).toBeNull();
    expect(parsed.stop_loss).toBeNull();
  });

  it("null Decimal 필드를 허용한다", () => {
    const parsed = OrderSchema.parse({
      ...BASE,
      reduce_only: false,
      trigger_price: null,
      trigger_by: null,
      take_profit: null,
      stop_loss: null,
    });
    expect(parsed.take_profit).toBeNull();
  });
});

describe("OrderSchema Wave2 fields", () => {
  it("Wave2 필드(trigger_direction/oco_group_id/trailing_stop) 를 parse 한다", () => {
    const parsed = OrderSchema.parse({
      ...BASE,
      trigger_direction: 2,
      oco_group_id: "oco-abc",
      trailing_stop: "120.5",
    });
    expect(parsed.trigger_direction).toBe(2);
    expect(parsed.oco_group_id).toBe("oco-abc");
    expect(parsed.trailing_stop).toBe("120.5");
  });

  it("Wave2 필드 누락 fixture 도 graceful 하게 parse 한다 (default null)", () => {
    const parsed = OrderSchema.parse(BASE);
    expect(parsed.trigger_direction).toBeNull();
    expect(parsed.oco_group_id).toBeNull();
    expect(parsed.trailing_stop).toBeNull();
  });
});

describe("OrderSchema Wave3 fields", () => {
  it("Wave3 필드가 없는 구 응답도 default null 로 parse 한다", () => {
    const parsed = OrderSchema.parse(BASE);
    expect(parsed.filled_quantity).toBeNull();
    expect(parsed.realized_pnl).toBeNull();
    expect(parsed.realized_pnl_synced_at).toBeNull();
  });

  it("Wave3 체결 수량·실현 손익·출처 마커를 그대로 parse 한다", () => {
    const parsed = OrderSchema.parse({
      ...BASE,
      filled_quantity: "0.005",
      realized_pnl: "12.34",
      realized_pnl_synced_at: "2026-06-26T10:01:00Z",
    });
    expect(parsed.filled_quantity).toBe("0.005");
    expect(parsed.realized_pnl).toBe("12.34");
    expect(parsed.realized_pnl_synced_at).toBe("2026-06-26T10:01:00Z");
  });
});
