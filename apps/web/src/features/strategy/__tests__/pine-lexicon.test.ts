import { describe, expect, it } from "vitest";
import {
  describeFunction,
  adviseError,
  adviseWarning,
  PINE_FUNCTION_LEXICON,
} from "@/features/strategy/pine-lexicon";

describe("PINE_FUNCTION_LEXICON", () => {
  it("covers 14 stdlib functions", () => {
    const stdlib = [
      "ta.sma",
      "ta.ema",
      "ta.rma",
      "ta.rsi",
      "ta.atr",
      "ta.stdev",
      "ta.crossover",
      "ta.crossunder",
      "ta.cross",
      "ta.highest",
      "ta.lowest",
      "ta.change",
      "nz",
      "na",
    ];
    for (const name of stdlib) {
      expect(PINE_FUNCTION_LEXICON[name], `missing: ${name}`).toBeDefined();
    }
  });

  it("describes known function with purpose + example", () => {
    const d = describeFunction("ta.rsi");
    expect(d.summary).toMatch(/RSI|상대.*강도/);
    expect(d.purpose.length).toBeGreaterThan(10);
    expect(d.example).toContain("ta.rsi");
  });

  it("returns fallback for unknown function", () => {
    const d = describeFunction("some.unknown.fn");
    expect(d.summary).toContain("some.unknown.fn");
    expect(d.purpose).toBeTruthy();
  });

  // T-G: schema guard — 새 엔트리 추가 시 빈 summary/purpose 회귀 방지
  it("every lexicon entry has non-empty summary and meaningful purpose", () => {
    const entries = Object.entries(PINE_FUNCTION_LEXICON);
    expect(entries.length).toBeGreaterThan(20);
    for (const [name, desc] of entries) {
      expect(desc.summary.length, `${name}: summary empty`).toBeGreaterThan(0);
      expect(desc.purpose.length, `${name}: purpose too short`).toBeGreaterThan(9);
    }
  });
});

describe("adviseError", () => {
  it("maps known code v4_migration to actionable hint", () => {
    const a = adviseError({
      code: "v4_migration",
      message: "rsi() is v4 syntax",
      line: 12,
    });
    expect(a.what).toBeTruthy();
    expect(a.action).toMatch(/ta\.|prefix/i);
  });

  it("falls back for unknown code", () => {
    const a = adviseError({ code: "mystery", message: "???", line: null });
    expect(a.what).toBeTruthy();
    expect(a.action).toBeTruthy();
  });
});

describe("adviseWarning", () => {
  it("detects duplicate strategy.exit pattern", () => {
    const a = adviseWarning(
      "duplicate strategy.exit calls at lines [10, 15]",
    );
    expect(a.what).toMatch(/exit/);
    expect(a.action).toMatch(/마지막/);
  });

  it("generic fallback for unknown warning", () => {
    const a = adviseWarning("some unknown warning");
    expect(a.what).toBeTruthy();
    expect(a.action).toBeTruthy();
  });
});
