// C13 — WalkForwardParamsSchema.best_params (옵티마이저 best_params OOS 주입) 검증.

import { describe, expect, it } from "vitest";

import { WalkForwardParamsSchema } from "../schemas";

describe("WalkForwardParamsSchema best_params", () => {
  const base = { train_bars: 500, test_bars: 100, max_folds: 20 } as const;

  it("best_params 없이 통과 (회귀 0 — 기존 caller 동작 불변)", () => {
    const parsed = WalkForwardParamsSchema.parse(base);
    expect(parsed.best_params).toBeUndefined();
  });

  it("best_params 숫자 record 통과", () => {
    const parsed = WalkForwardParamsSchema.parse({
      ...base,
      best_params: { ema: 20, sl: 2.5 },
    });
    expect(parsed.best_params).toEqual({ ema: 20, sl: 2.5 });
  });

  it("non-finite best_params value reject (Decimal-first 안전)", () => {
    expect(() =>
      WalkForwardParamsSchema.parse({
        ...base,
        best_params: { ema: Number.POSITIVE_INFINITY },
      }),
    ).toThrow();
  });
});
