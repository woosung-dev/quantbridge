// 리포트 FE 파생 계산 단위 테스트 — 분포/승패/커브 range/B&H/초과수익 (손계산 golden)
import { describe, expect, it } from "vitest";

import {
  binReturnDistribution,
  computeCurveRange,
  computeExcessReturn,
  computeOutcomeCounts,
  deriveBuyAndHoldMetrics,
} from "../analytics";

describe("binReturnDistribution", () => {
  it("equal-width buckets over [min,max] — 손계산 golden", () => {
    // returns: -0.02, 0.00, 0.01, 0.03, 0.04 → min -0.02, max 0.04, 폭 0.03 (2버킷)
    const bins = binReturnDistribution([-0.02, 0, 0.01, 0.03, 0.04], 2);
    expect(bins).toHaveLength(2);
    expect(bins[0]!.from).toBeCloseTo(-0.02, 10);
    expect(bins[0]!.to).toBeCloseTo(0.01, 10);
    expect(bins[0]!.count).toBe(2); // -0.02, 0.00 (0.01 은 두 번째 버킷 하한)
    expect(bins[1]!.count).toBe(3); // 0.01, 0.03, 0.04 (max 는 마지막 버킷 포함)
  });

  it("empty → [], 단일 값 → 1버킷", () => {
    expect(binReturnDistribution([], 10)).toEqual([]);
    expect(binReturnDistribution([0.05, 0.05], 10)).toEqual([
      { from: 0.05, to: 0.05, count: 2 },
    ]);
  });

  it("non-finite 값 무시", () => {
    const bins = binReturnDistribution([Number.NaN, 0.01, 0.02], 1);
    expect(bins[0]!.count).toBe(2);
  });
});

describe("computeOutcomeCounts", () => {
  it("승/패/손익분기 분류", () => {
    expect(computeOutcomeCounts([10, -5, 0, 3])).toEqual({
      wins: 2,
      losses: 1,
      breakeven: 1,
      total: 4,
    });
  });

  it("빈 배열 → 전부 0", () => {
    expect(computeOutcomeCounts([])).toEqual({
      wins: 0,
      losses: 0,
      breakeven: 0,
      total: 0,
    });
  });
});

describe("computeCurveRange", () => {
  it("첫 값 기준 최대/현재/최소 % — 손계산", () => {
    // base 100: [100, 120, 90, 110] → max 0.2, min -0.1, current 0.1
    const range = computeCurveRange([100, 120, 90, 110]);
    expect(range).not.toBeNull();
    expect(range!.maxPct).toBeCloseTo(0.2, 10);
    expect(range!.minPct).toBeCloseTo(-0.1, 10);
    expect(range!.currentPct).toBeCloseTo(0.1, 10);
  });

  it("2점 미만 / base 0 → null", () => {
    expect(computeCurveRange([100])).toBeNull();
    expect(computeCurveRange([0, 10])).toBeNull();
  });
});

describe("deriveBuyAndHoldMetrics", () => {
  it("수익률 + 종가 기준 MDD — 손계산", () => {
    // [100, 120, 90, 110]: return 0.1 / MDD = (90-120)/120 = -0.25
    const m = deriveBuyAndHoldMetrics([100, 120, 90, 110]);
    expect(m).not.toBeNull();
    expect(m!.returnPct).toBeCloseTo(0.1, 10);
    expect(m!.maxDrawdownPct).toBeCloseTo(-0.25, 10);
  });

  it("non-finite 포함 → null (거짓 값 렌더 금지)", () => {
    expect(deriveBuyAndHoldMetrics([100, Number.NaN, 110])).toBeNull();
  });
});

describe("computeExcessReturn", () => {
  it("전략 - B&H 절대/상대 — 손계산", () => {
    // equity 12000 vs BH 11000, 초기 10000 → abs 1000, pct 0.1
    expect(computeExcessReturn(12000, 11000, 10000)).toEqual({
      abs: 1000,
      pct: 0.1,
    });
  });

  it("초기자본 0 / non-finite → null", () => {
    expect(computeExcessReturn(12000, 11000, 0)).toBeNull();
    expect(computeExcessReturn(Number.NaN, 11000, 10000)).toBeNull();
  });
});
