// Sprint FE-04: downsample + formatter unit tests.

import { describe, expect, it } from "vitest";

import type { EquityPoint } from "../schemas";
import {
  downsampleEquity,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatPercent,
} from "../utils";

function mkPoints(n: number): EquityPoint[] {
  return Array.from({ length: n }, (_, i) => ({
    timestamp: new Date(Date.UTC(2024, 0, 1 + i)).toISOString(),
    value: 10000 + i,
  }));
}

describe("downsampleEquity", () => {
  it("returns points unchanged when n <= max", () => {
    const pts = mkPoints(500);
    const result = downsampleEquity(pts, 1000);
    expect(result.length).toBe(500);
    expect(result[0]).toEqual(pts[0]);
    expect(result[499]).toEqual(pts[499]);
  });

  it("reduces 2000 points to <= 1000 preserving first and last", () => {
    const pts = mkPoints(2000);
    const result = downsampleEquity(pts, 1000);
    expect(result.length).toBeLessThanOrEqual(1000);
    expect(result[0]).toEqual(pts[0]);
    expect(result[result.length - 1]).toEqual(pts[1999]);
  });

  it("handles exact multiple", () => {
    const pts = mkPoints(3000);
    const result = downsampleEquity(pts, 1000);
    expect(result.length).toBeLessThanOrEqual(1000);
    expect(result[0]).toEqual(pts[0]);
    expect(result[result.length - 1]).toEqual(pts[2999]);
  });

  it("throws on max <= 1", () => {
    expect(() => downsampleEquity(mkPoints(10), 1)).toThrow();
  });
});

describe("formatPercent", () => {
  it("converts fraction to percent with 2 decimals", () => {
    expect(formatPercent(0.1523)).toBe("15.23%");
  });
  it("handles negative", () => {
    expect(formatPercent(-0.05)).toBe("-5.00%");
  });
  it("returns em dash for non-finite", () => {
    expect(formatPercent(Number.NaN)).toBe("—");
  });
});

describe("formatCurrency", () => {
  it("formats with thousands separator and 2 decimals", () => {
    expect(formatCurrency(12345.678)).toBe("12,345.68");
  });
  it("returns em dash for non-finite", () => {
    expect(formatCurrency(Number.POSITIVE_INFINITY)).toBe("—");
  });
});

describe("formatDate", () => {
  it("formats ISO to YYYY-MM-DD (UTC)", () => {
    expect(formatDate("2024-03-15T18:30:00+00:00")).toBe("2024-03-15");
  });
});

describe("formatDateTime", () => {
  it("formats ISO to YYYY-MM-DD HH:mm (UTC)", () => {
    expect(formatDateTime("2024-03-15T18:30:00+00:00")).toBe("2024-03-15 18:30");
  });
  it("returns em dash for null", () => {
    expect(formatDateTime(null)).toBe("—");
  });
});
