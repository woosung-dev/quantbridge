// Sprint 33 BL-175 hotfix (2026-05-05, dogfood Day 6 발견):
// computeBuyAndHold 가 항상 빈 배열 반환 = BH series 미렌더 + ChartLegend BH 항목
// 미표시. 진짜 Buy & Hold 는 자산 OHLCV 의존 (backend 구현 = Sprint 34 BL-175).
// 본 test 는 거짓 trust 차단 검증 (legend 와 chart 데이터 mismatch 0건).

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

describe("computeBuyAndHold (BL-175 hotfix)", () => {
  it("returns empty array for empty equity curve", () => {
    expect(computeBuyAndHold([], 10000)).toEqual([]);
  });

  it("returns empty array always — BL-175 거짓 trust 차단", () => {
    // Sprint 33 hotfix: BE buy_and_hold_curve 신규 구현 전까지 frontend 자체 계산 금지.
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

  it("returns empty array even when equity curve has self-flagged invalid first value", () => {
    const bad: EquityPoint[] = [
      { timestamp: "2026-01-01T00:00:00Z", value: 0 },
      { timestamp: "2026-01-02T00:00:00Z", value: 10000 },
    ];
    expect(computeBuyAndHold(bad, 10000)).toEqual([]);
  });

  it("returns empty array when last equity is negative (자본 초과 손실 = 본 BUG 의 root scenario)", () => {
    // Sprint 32 BL-156 mdd_exceeds_capital=true scenario.
    // 기존 구현: endBh = initialCapital * (-92220 / 10000) = -92220 → BH line 이
    //   strategy line 과 동일 = legend mismatch.
    // hotfix: 빈 배열 반환 = BH series 미추가 = legend 도 자동 hide.
    const lossCurve: EquityPoint[] = [
      { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
      { timestamp: "2026-01-05T00:00:00Z", value: -92220 },
    ];
    expect(computeBuyAndHold(lossCurve, 10000)).toEqual([]);
  });
});
