import { describe, expect, it } from "vitest";

import { computeBuyAndHold } from "../utils";
import type { EquityPoint } from "../schemas";

const CURVE: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 10500 },
  { timestamp: "2026-01-03T00:00:00Z", value: 11000 },
  { timestamp: "2026-01-04T00:00:00Z", value: 12000 },
  { timestamp: "2026-01-05T00:00:00Z", value: 12500 },
];

describe("computeBuyAndHold", () => {
  it("returns empty array for empty equity curve", () => {
    expect(computeBuyAndHold([], 10000)).toEqual([]);
  });

  it("returns empty array when initialCapital <= 0 (guard)", () => {
    expect(computeBuyAndHold(CURVE, 0)).toEqual([]);
    expect(computeBuyAndHold(CURVE, -100)).toEqual([]);
  });

  it("returns empty array when initialCapital is not finite", () => {
    expect(computeBuyAndHold(CURVE, Number.NaN)).toEqual([]);
    expect(computeBuyAndHold(CURVE, Number.POSITIVE_INFINITY)).toEqual([]);
  });

  it("returns single point with initialCapital when curve has 1 point", () => {
    const result = computeBuyAndHold(
      [{ timestamp: "2026-01-01T00:00:00Z", value: 10000 }],
      5000,
    );
    expect(result).toHaveLength(1);
    expect(result[0]!.value).toBe(5000);
    expect(result[0]!.timestamp).toBe("2026-01-01T00:00:00Z");
  });

  it("matches initialCapital at first point and (initialCapital * last/first) at last point", () => {
    const result = computeBuyAndHold(CURVE, 10000);
    expect(result).toHaveLength(CURVE.length);

    // 첫 시점 = initialCapital.
    expect(result[0]!.value).toBeCloseTo(10000, 6);
    // 마지막 시점 = 10000 * (12500 / 10000) = 12500.
    expect(result[result.length - 1]!.value).toBeCloseTo(12500, 6);
    // timestamp 시퀀스 보존.
    expect(result.map((p) => p.timestamp)).toEqual(
      CURVE.map((p) => p.timestamp),
    );
  });

  it("performs linear interpolation between first and last (mid-point check)", () => {
    // 5 포인트, 첫 10000 → 끝 12500. 정확히 mid (idx=2) = 11250.
    const result = computeBuyAndHold(CURVE, 10000);
    expect(result[2]!.value).toBeCloseTo(11250, 6);
    // idx=1 = 10000 + (12500-10000) * (1/4) = 10625.
    expect(result[1]!.value).toBeCloseTo(10625, 6);
    // idx=3 = 10000 + (12500-10000) * (3/4) = 11875.
    expect(result[3]!.value).toBeCloseTo(11875, 6);
  });

  it("returns empty array when first equity is non-positive (guard)", () => {
    const bad: EquityPoint[] = [
      { timestamp: "2026-01-01T00:00:00Z", value: 0 },
      { timestamp: "2026-01-02T00:00:00Z", value: 10000 },
    ];
    expect(computeBuyAndHold(bad, 10000)).toEqual([]);
  });
});
