import { describe, expect, it } from "vitest";

import { ExchangeAccountSchema } from "../schemas";

describe("ExchangeAccountSchema", () => {
  it("exchange_uid와 read_only를 보존한다", () => {
    const account = ExchangeAccountSchema.parse({
      id: "b0000000-0000-4000-8000-000000000001",
      exchange: "bybit",
      mode: "demo",
      label: "Bybit 데모",
      api_key_masked: "ABCD******WXYZ",
      exchange_uid: "558689281",
      read_only: true,
      created_at: "2026-07-28T00:00:00Z",
    });

    expect(account.exchange_uid).toBe("558689281");
    expect(account.read_only).toBe(true);
  });
});
