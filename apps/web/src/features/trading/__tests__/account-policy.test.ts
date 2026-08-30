import { describe, expect, it } from "vitest";

import { isBybitDemoAccount } from "../account-policy";

describe("isBybitDemoAccount", () => {
  it("Bybit Demo 계정만 사용자 거래 대상으로 인정한다", () => {
    expect(isBybitDemoAccount({ exchange: "bybit", mode: "demo" })).toBe(true);
  });

  it.each([
    { exchange: "bybit", mode: "live" },
    { exchange: "okx", mode: "demo" },
    { exchange: "binance", mode: "live" },
  ])("legacy %o 계정은 거래 대상에서 제외한다", (account) => {
    expect(isBybitDemoAccount(account)).toBe(false);
  });
});
