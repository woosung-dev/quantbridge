// 청산가 크로스도메인 계약(W-B) — schema parse + queryKey factory + api POST 검증.

import { afterEach, describe, expect, it, vi } from "vitest";

import { tradingKeys } from "../query-keys";
import { LiquidationInfoResponseSchema } from "../schemas";

// api.ts 가 import 하는 apiFetch 를 mock — getLiquidationInfo 호출 shape 검증용.
const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({
  apiFetch: apiFetchMock,
  ApiError: class ApiError extends Error {},
}));

import { getLiquidationInfo } from "../api";

describe("LiquidationInfoResponseSchema", () => {
  it("W-B 계약 응답을 parse 한다 (Decimal→string)", () => {
    const parsed = LiquidationInfoResponseSchema.parse({
      symbol: "BTCUSDT",
      entry_price: "50000",
      side: "buy",
      leverage: 10,
      liquidation_price: "45500",
      maintenance_margin_rate: "0.005",
      distance_pct: "9.0",
    });
    expect(parsed.liquidation_price).toBe("45500");
    expect(parsed.leverage).toBe(10);
  });

  it("필드 누락 시 reject 한다 (1:1 계약 강제)", () => {
    const result = LiquidationInfoResponseSchema.safeParse({
      symbol: "BTCUSDT",
      entry_price: "50000",
    });
    expect(result.success).toBe(false);
  });
});

describe("tradingKeys.liquidation", () => {
  it("userId 를 첫 인자로 둔다 (LESSON-005)", () => {
    const key = tradingKeys.liquidation("user-1", {
      symbol: "BTCUSDT",
      side: "buy",
      entry_price: "50000",
      leverage: 10,
    });
    expect(key[0]).toBe("trading");
    expect(key[1]).toBe("user-1");
    expect(key).toContain("liquidation");
    expect(key).toContain("BTCUSDT");
  });

  it("입력 파라미터가 다르면 다른 key 를 만든다", () => {
    const a = tradingKeys.liquidation("u", {
      symbol: "BTCUSDT",
      side: "buy",
      entry_price: "50000",
      leverage: 10,
    });
    const b = tradingKeys.liquidation("u", {
      symbol: "BTCUSDT",
      side: "sell",
      entry_price: "50000",
      leverage: 10,
    });
    expect(JSON.stringify(a)).not.toBe(JSON.stringify(b));
  });
});

describe("getLiquidationInfo", () => {
  afterEach(() => {
    apiFetchMock.mockReset();
  });

  it("POST /api/v1/liquidation/preview + JSON body 로 호출하고 응답을 parse 한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      symbol: "BTCUSDT",
      entry_price: "50000",
      side: "buy",
      leverage: 10,
      liquidation_price: "45500",
      maintenance_margin_rate: "0.005",
      distance_pct: "9.0",
    });

    const result = await getLiquidationInfo(
      { symbol: "BTCUSDT", side: "buy", entry_price: "50000", leverage: 10 },
      "tok",
    );

    expect(result.liquidation_price).toBe("45500");
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    const [path, opts] = apiFetchMock.mock.calls[0] as [
      string,
      {
        method: string;
        token: string | null;
        body?: unknown;
        params?: unknown;
      },
    ];
    expect(path).toBe("/api/v1/liquidation/preview");
    expect(opts.method).toBe("POST");
    expect(opts.token).toBe("tok");
    // params(GET 쿼리) 가 아니라 body(JSON) 로 전달 — 버그 회귀 차단.
    expect(opts.params).toBeUndefined();
    expect(opts.body).toEqual({
      symbol: "BTCUSDT",
      side: "buy",
      entry_price: "50000",
      leverage: 10,
    });
  });
});
