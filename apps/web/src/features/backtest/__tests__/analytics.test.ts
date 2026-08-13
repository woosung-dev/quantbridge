// 리포트 FE 파생 계산 단위 테스트 — 분포/승패/커브 range/B&H/초과수익 (손계산 golden)
import { describe, expect, it } from "vitest";

import {
  binReturnDistribution,
  computeProfitStructure,
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

describe("computeProfitStructure", () => {
  const t = (pnl: number, fees: number, extra: object = {}) => ({
    status: "closed",
    pnl,
    fees,
    ...extra,
  });

  it("비용 전 gross 분해 + 항등식 (grossProfit - grossLoss - fees - slippage === net)", () => {
    // T1: net +10, cost 2 → gross +12 / T2: net -5, cost 3 → gross -2
    const s = computeProfitStructure([
      t(10, 2, { fee_paid: 1.5, slippage_paid: 0.5 }),
      t(-5, 3, { fee_paid: 2, slippage_paid: 1 }),
    ]);
    expect(s).not.toBeNull();
    expect(s!.grossProfit).toBeCloseTo(12, 10);
    expect(s!.grossLoss).toBeCloseTo(2, 10);
    expect(s!.fees).toBeCloseTo(3.5, 10);
    expect(s!.slippage).toBeCloseTo(1.5, 10);
    expect(s!.net).toBeCloseTo(5, 10);
    expect(s!.grossProfit - s!.grossLoss - s!.fees - s!.slippage).toBeCloseTo(s!.net, 10);
  });

  it("fee/slip 미분리 구 데이터 → 결합 비용을 수수료 축으로 (항등식 유지)", () => {
    const s = computeProfitStructure([t(10, 2), t(-5, 3)]);
    expect(s!.fees).toBeCloseTo(5, 10);
    expect(s!.slippage).toBe(0);
    expect(s!.grossProfit - s!.grossLoss - s!.fees - s!.slippage).toBeCloseTo(s!.net, 10);
  });

  it("closed 0건 → null (open 만 있으면 waterfall 잠금)", () => {
    expect(computeProfitStructure([])).toBeNull();
    expect(computeProfitStructure([{ status: "open", pnl: 0, fees: 1 }])).toBeNull();
  });
});

describe("binReturnDistribution — 대용량 입력", () => {
  // 예전 구현은 `Math.min(...finite)` 였다. spread 는 인자 개수 상한이라
  // Node 22 실측 ≈ 124,000 부터 RangeError 를 던지고, 그러면 리포트의
  // 수익률 분포 섹션이 통째로 렌더되지 않는다.
  it("13만 건에서도 던지지 않고 경계값을 정확히 잡는다", () => {
    const returns = Array.from({ length: 130_000 }, (_, i) => (i % 200) / 1_000);
    // 최소/최대를 배열 양 끝이 아닌 중간에 심어 전 구간 스캔을 강제한다.
    returns[65_000] = -0.5;
    returns[65_001] = 0.75;

    const bins = binReturnDistribution(returns, 10);

    expect(bins).toHaveLength(10);
    expect(bins[0]?.from).toBeCloseTo(-0.5, 10);
    expect(bins[9]?.to).toBeCloseTo(0.75, 10);
    const counted = bins.reduce((sum, b) => sum + b.count, 0);
    expect(counted).toBe(returns.length);
  });
});
