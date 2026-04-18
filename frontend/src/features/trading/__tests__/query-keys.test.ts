// Sprint FE-02: tradingKeys factory identity 검증.

import { describe, expect, it } from "vitest";

import { tradingKeys } from "../query-keys";

describe("tradingKeys", () => {
  it("prepends userId to root key", () => {
    expect(tradingKeys.all("user_abc")).toEqual(["trading", "user_abc"]);
  });

  it("orders key includes userId and limit", () => {
    const key = tradingKeys.orders("user_a", 50);
    expect(key).toEqual(["trading", "user_a", "orders", 50]);
  });

  it("different userId isolates orders cache for same limit", () => {
    const a = tradingKeys.orders("user_a", 50);
    const b = tradingKeys.orders("user_b", 50);
    expect(a).not.toEqual(b);
  });

  it("killSwitch key scoped to userId", () => {
    expect(tradingKeys.killSwitch("user_k")).toEqual([
      "trading",
      "user_k",
      "kill-switch",
    ]);
  });

  it("exchangeAccounts key scoped to userId", () => {
    expect(tradingKeys.exchangeAccounts("user_e")).toEqual([
      "trading",
      "user_e",
      "exchange-accounts",
    ]);
  });
});
