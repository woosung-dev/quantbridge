import { describe, it, expect } from "vitest";

// 누적 PnL 계산 로직 (trade-table.tsx useMemo 동일 알고리즘)
function calcCumulative(pnls: number[]): number[] {
  let cum = 0;
  return pnls.map((pnl) => {
    cum += pnl;
    return cum;
  });
}

describe("cumulative PnL calculation", () => {
  it("단일 거래: 해당 PnL 그대로", () => {
    expect(calcCumulative([100])).toEqual([100]);
  });

  it("복수 거래: 누적 합산", () => {
    expect(calcCumulative([100, -50, 30])).toEqual([100, 50, 80]);
  });

  it("빈 배열: 빈 배열 반환", () => {
    expect(calcCumulative([])).toEqual([]);
  });

  it("모두 손실: 음수 누적", () => {
    expect(calcCumulative([-10, -20])).toEqual([-10, -30]);
  });

  it("모두 수익: 양수 누적", () => {
    expect(calcCumulative([5, 10, 15])).toEqual([5, 15, 30]);
  });
});
