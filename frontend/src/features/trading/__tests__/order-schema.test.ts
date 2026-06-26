// OrderSchema Wave1 TP/SL 필드 1:1 검증 — BE OrderResponse 와 정합.

import { describe, expect, it } from "vitest";

import { OrderSchema } from "../schemas";

const BASE = {
  id: "a0000000-0000-4000-a000-000000000001",
  symbol: "BTCUSDT",
  side: "buy" as const,
  state: "filled" as const,
  quantity: "0.01",
  filled_price: "50000",
  exchange_order_id: "broker-1",
  error_message: null,
  created_at: "2026-06-26T10:00:00Z",
};

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
