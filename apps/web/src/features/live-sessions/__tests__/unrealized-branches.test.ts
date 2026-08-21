// 미실현 손익의 short 방향과 거래 스키마 거절 경계를 고정한다.
import { describe, expect, it } from "vitest";

import { computeUnrealizedPnl, OpenTradeSchema } from "../unrealized";

describe("computeUnrealizedPnl 추가 분기", () => {
  it("공백이 있는 유한 mark 가격에서도 short 손익 방향을 반대로 계산한다", () => {
    expect(
      computeUnrealizedPnl(
        [
          { direction: "short", qty: 2, entry_price: 100 },
          { direction: "long", qty: 1, entry_price: 80 },
        ],
        " 90 ",
      ),
    ).toBe(30);
  });

  it("OpenTradeSchema 밖의 방향은 파싱과 손익 계산 모두에서 거절한다", () => {
    const invalidTrade = { direction: "flat", qty: 1, entry_price: 100 };

    expect(OpenTradeSchema.safeParse(invalidTrade).success).toBe(false);
    expect(computeUnrealizedPnl([invalidTrade] as never, "90")).toBeNull();
  });
});
