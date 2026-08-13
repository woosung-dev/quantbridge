// normalizeToPnlCurve helper 의 5 acceptance (Sprint 37 BL-184).

import { describe, expect, it } from "vitest";

import {
  normalizeToPercentCurve,
  normalizeToPnlCurve,
} from "../normalize-to-pnl-curve";

describe("normalizeToPnlCurve — Sprint 37 BL-184", () => {
  it("returns empty array for empty input", () => {
    expect(normalizeToPnlCurve([])).toEqual([]);
  });

  it("normalizes a single point to value 0", () => {
    const out = normalizeToPnlCurve([{ value: 100 }]);
    expect(out).toEqual([{ value: 0 }]);
  });

  it("subtracts the first value from every point (PnL 기준)", () => {
    const out = normalizeToPnlCurve([
      { value: 100 },
      { value: 150 },
      { value: 80 },
    ]);
    expect(out).toEqual([{ value: 0 }, { value: 50 }, { value: -20 }]);
  });

  it("is idempotent — normalize(normalize(x)) === normalize(x)", () => {
    const input = [
      { value: 10000 },
      { value: 10200 },
      { value: 9800 },
      { value: 10500 },
    ];
    const once = normalizeToPnlCurve(input);
    const twice = normalizeToPnlCurve(once);
    expect(twice).toEqual(once);
  });

  it("preserves non-value fields (time, color, etc.)", () => {
    const input = [
      { value: 100, timestamp: "2026-01-01T00:00:00Z", label: "start" },
      { value: 150, timestamp: "2026-01-02T00:00:00Z", label: "mid" },
    ];
    const out = normalizeToPnlCurve(input);
    expect(out).toEqual([
      { value: 0, timestamp: "2026-01-01T00:00:00Z", label: "start" },
      { value: 50, timestamp: "2026-01-02T00:00:00Z", label: "mid" },
    ]);
  });
});

describe("normalizeToPercentCurve — Compare 오버레이 (% 수익률)", () => {
  it("returns empty array for empty input", () => {
    expect(normalizeToPercentCurve([])).toEqual([]);
  });

  it("normalizes a single point to 0%", () => {
    expect(normalizeToPercentCurve([{ value: 100 }])).toEqual([{ value: 0 }]);
  });

  it("computes percent return relative to the first value (시작=0%)", () => {
    const out = normalizeToPercentCurve([
      { value: 100 },
      { value: 150 },
      { value: 80 },
    ]);
    expect(out[0]!.value).toBeCloseTo(0, 9);
    expect(out[1]!.value).toBeCloseTo(50, 9);
    expect(out[2]!.value).toBeCloseTo(-20, 9);
  });

  it("is capital-agnostic — 두 자본금이 달라도 동일 % 곡선", () => {
    const small = normalizeToPercentCurve([{ value: 100 }, { value: 120 }]);
    const large = normalizeToPercentCurve([
      { value: 1_000_000 },
      { value: 1_200_000 },
    ]);
    expect(small).toEqual(large); // 둘 다 [0, 20]
  });

  it("guards a zero/non-finite baseline → 0", () => {
    expect(normalizeToPercentCurve([{ value: 0 }, { value: 50 }])).toEqual([
      { value: 0 },
      { value: 0 },
    ]);
  });

  it("preserves non-value fields", () => {
    const out = normalizeToPercentCurve([
      { value: 200, timestamp: "2026-01-01T00:00:00Z" },
      { value: 250, timestamp: "2026-01-02T00:00:00Z" },
    ]);
    expect(out).toEqual([
      { value: 0, timestamp: "2026-01-01T00:00:00Z" },
      { value: 25, timestamp: "2026-01-02T00:00:00Z" },
    ]);
  });
});
