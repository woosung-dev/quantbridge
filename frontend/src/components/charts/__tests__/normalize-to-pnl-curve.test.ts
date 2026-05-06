// normalizeToPnlCurve helper 의 5 acceptance (Sprint 37 BL-184).

import { describe, expect, it } from "vitest";

import { normalizeToPnlCurve } from "../normalize-to-pnl-curve";

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
