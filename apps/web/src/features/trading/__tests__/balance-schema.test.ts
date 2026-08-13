// 거래소 계정 잔고 계약의 Decimal 문자열·null 허용을 검증한다.
import { describe, expect, it } from "vitest";

import { AccountBalanceSchema } from "../schemas";

const balance = {
  account_id: "a0000000-0000-4000-8000-000000000001",
  asset: "USDT",
  supported: true,
  reason: null,
  total: "123.456789",
  free: "100.000001",
  fetched_at: "2026-07-24T12:00:00Z",
};

describe("AccountBalanceSchema", () => {
  it("Decimal을 number로 바꾸지 않고 문자열로 보존한다", () => {
    expect(AccountBalanceSchema.parse(balance)).toEqual(balance);
  });

  it("지원되더라도 total과 free가 null일 수 있다", () => {
    expect(AccountBalanceSchema.parse({ ...balance, total: null, free: null })).toMatchObject({
      supported: true,
      total: null,
      free: null,
    });
  });
});
