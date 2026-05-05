// Sprint 34 BL-175 본격 fix (2026-05-05):
// computeBuyAndHold 는 legacy no-op (deprecated). backend `metrics.buy_and_hold_curve`
// (OHLCV 첫/끝 close 기반 정확 계산) 가 진짜 BH curve 제공. frontend 자체 계산은 폐기.
//
// 본 test 는 backward import compat + 영구 no-op 동작 검증 (regression 차단).
// EquityChartV2 의 신규 buyAndHoldCurve prop wiring 검증은 equity-chart-v2.test.tsx 참조.

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

describe("computeBuyAndHold (Sprint 34 BL-175 — legacy no-op)", () => {
  it("returns empty array for empty equity curve", () => {
    expect(computeBuyAndHold([], 10000)).toEqual([]);
  });

  it("returns empty array for any non-empty curve — frontend 자체 계산 폐기", () => {
    // Sprint 34: backend metrics.buy_and_hold_curve 사용. frontend 자체 계산 영구 폐기.
    expect(computeBuyAndHold(CURVE, 10000)).toEqual([]);
  });

  it("returns empty array for single point curve", () => {
    expect(
      computeBuyAndHold(
        [{ timestamp: "2026-01-01T00:00:00Z", value: 10000 }],
        5000,
      ),
    ).toEqual([]);
  });

  it("returns empty array regardless of initialCapital", () => {
    expect(computeBuyAndHold(CURVE, 0)).toEqual([]);
    expect(computeBuyAndHold(CURVE, -100)).toEqual([]);
    expect(computeBuyAndHold(CURVE, Number.NaN)).toEqual([]);
    expect(computeBuyAndHold(CURVE, Number.POSITIVE_INFINITY)).toEqual([]);
  });

  it("returns empty array when curve contains negative or zero equity", () => {
    // 자본 초과 손실 (Sprint 32 BL-156 mdd_exceeds_capital=true) 시나리오에서도
    // 거짓 BH line 미렌더 — Surface Trust ADR-019 정합.
    const lossCurve: EquityPoint[] = [
      { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
      { timestamp: "2026-01-05T00:00:00Z", value: -92220 },
    ];
    expect(computeBuyAndHold(lossCurve, 10000)).toEqual([]);
  });
});
