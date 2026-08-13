// 실시간 envelope의 백엔드 계약 미러와 미지 이벤트 무시를 검증한다.
import { describe, expect, it } from "vitest";

import { parseRealtimeEnvelope } from "./schemas";

describe("parseRealtimeEnvelope", () => {
  it("유효한 order_update envelope를 round-trip 한다", () => {
    const raw = {
      v: 1,
      type: "order_update",
      ts: 1_720_000_000,
      payload: {
        order_id: "order-1",
        state: "filled",
        symbol: "BTC/USDT",
        side: "buy",
        source: "exchange",
      },
    };

    expect(parseRealtimeEnvelope(JSON.stringify(raw))).toEqual(raw);
  });

  it("유효한 ticker envelope를 round-trip 한다", () => {
    const raw = {
      v: 1,
      type: "ticker",
      ts: 1_720_000_000,
      payload: {
        symbol: "BTCUSDT",
        mark_price: "67000.25",
        last_price: "67000.00",
      },
    };

    expect(parseRealtimeEnvelope(JSON.stringify(raw))).toEqual(raw);
  });

  it("position_update는 long·short·flat 계약만 허용한다", () => {
    const raw = {
      v: 1,
      type: "position_update",
      ts: 1_720_000_000,
      payload: { symbol: "BTCUSDT", side: "flat", size: "0" },
    };

    expect(parseRealtimeEnvelope(JSON.stringify(raw))).toEqual(raw);
    expect(
      parseRealtimeEnvelope(JSON.stringify({ ...raw, payload: { ...raw.payload, side: "buy" } })),
    ).toBeNull();
  });

  it("미지 타입과 잘못된 JSON은 조용히 무시한다", () => {
    expect(parseRealtimeEnvelope('{"v":1,"type":"future_event","ts":1,"payload":{}}')).toBeNull();
    expect(parseRealtimeEnvelope("not-json")).toBeNull();
  });
});
