// 실현손익 string → 부호·tone 포맷 헬퍼 단위 테스트.
import { describe, it, expect } from "vitest";
import { formatRealizedPnl } from "../utils";

describe("formatRealizedPnl", () => {
  it("양수 → + prefix + profit tone", () => {
    expect(formatRealizedPnl("12.34")).toEqual({ text: "+12.34", tone: "profit" });
  });
  it("음수 → 부호 보존 + loss tone", () => {
    expect(formatRealizedPnl("-5.5")).toEqual({ text: "-5.5", tone: "loss" });
  });
  it("0 → flat tone, prefix 없음", () => {
    expect(formatRealizedPnl("0")).toEqual({ text: "0", tone: "flat" });
  });
  it("파싱 불가 → raw 보존 + flat tone", () => {
    expect(formatRealizedPnl("n/a")).toEqual({ text: "n/a", tone: "flat" });
  });
  it("precision 보존 — 원본 string 유지(부동소수 재포맷 안 함)", () => {
    expect(formatRealizedPnl("0.000000001")).toEqual({
      text: "+0.000000001",
      tone: "profit",
    });
  });
});
