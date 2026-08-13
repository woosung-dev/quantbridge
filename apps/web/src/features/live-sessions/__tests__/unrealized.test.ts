// WS 마크가격 기반 미실현 손익의 정직한 계산 경계를 검증한다.
import { describe, expect, it } from "vitest";

import { computeUnrealizedPnl } from "../unrealized";

const trades = [
  { direction: "long" as const, qty: 2, entry_price: 100 },
  { direction: "short" as const, qty: 3, entry_price: 120 },
];

describe("computeUnrealizedPnl", () => {
  it("long·short 여러 미청산 거래를 합산한다", () => {
    // long: (110 - 100) × 2 = 20, short: (110 - 120) × 3 × -1 = 30
    expect(computeUnrealizedPnl(trades, "110")).toBe(50);
  });

  it("빈 거래 배열은 0으로 계산한다", () => {
    expect(computeUnrealizedPnl([], "110")).toBe(0);
  });

  it.each(["", "   ", "abc", "Infinity", "-Infinity"])(
    "빈 문자열·비유한 mark %j를 거절한다",
    (markPrice) => {
      expect(computeUnrealizedPnl(trades, markPrice)).toBeNull();
    },
  );

  it("원소 parse 실패와 비유한 trade 숫자는 부분 합산하지 않고 전체를 거절한다", () => {
    expect(
      computeUnrealizedPnl(
        [
          { direction: "long", qty: 1, entry_price: 100 },
          { direction: "long", qty: "1", entry_price: 100 },
        ] as never,
        "110",
      ),
    ).toBeNull();
    expect(
      computeUnrealizedPnl([{ direction: "long", qty: Number.NaN, entry_price: 100 }], "110"),
    ).toBeNull();
  });
});
