// mergeCumulativeCurves — 여러 세션 누적 PnL 곡선 병합 순수 헬퍼 검증

import { describe, expect, it } from "vitest";

import { mergeCumulativeCurves } from "../aggregate";

describe("mergeCumulativeCurves", () => {
  it("returns empty for no curves", () => {
    expect(mergeCumulativeCurves([])).toEqual([]);
  });

  it("returns empty when all curves are empty", () => {
    expect(mergeCumulativeCurves([[], []])).toEqual([]);
  });

  it("passes through a single curve unchanged", () => {
    const c = [
      { time: 1, value: 10 },
      { time: 2, value: 25 },
    ];
    expect(mergeCumulativeCurves([c])).toEqual(c);
  });

  it("sums two curves with carry-forward at the union of timestamps", () => {
    // A: t1=10, t3=30 ; B: t2=5, t3=8
    const a = [
      { time: 1, value: 10 },
      { time: 3, value: 30 },
    ];
    const b = [
      { time: 2, value: 5 },
      { time: 3, value: 8 },
    ];
    // t1: A=10, B=0 → 10 ; t2: A=10(carry), B=5 → 15 ; t3: A=30, B=8 → 38
    expect(mergeCumulativeCurves([a, b])).toEqual([
      { time: 1, value: 10 },
      { time: 2, value: 15 },
      { time: 3, value: 38 },
    ]);
  });

  it("sorts unsorted input before merging", () => {
    const a = [
      { time: 3, value: 30 },
      { time: 1, value: 10 },
    ];
    expect(mergeCumulativeCurves([a])).toEqual([
      { time: 1, value: 10 },
      { time: 3, value: 30 },
    ]);
  });

  it("ignores empty curves mixed with populated ones", () => {
    const a = [{ time: 5, value: 100 }];
    expect(mergeCumulativeCurves([[], a, []])).toEqual([
      { time: 5, value: 100 },
    ]);
  });
});
