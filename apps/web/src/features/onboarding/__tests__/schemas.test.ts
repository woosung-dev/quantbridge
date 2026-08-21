// Onboarding persist payload의 Zod runtime 계약을 고정한다.
// zustand rehydrate 전 데이터 검증만 측정하며 store는 렌더하지 않는다.

import { describe, expect, it } from "vitest";

import {
  OnboardingPersistSchema,
  OnboardingStepSchema,
} from "@/features/onboarding/schemas";
import { ONBOARDING_VERSION } from "@/features/onboarding/types";

const STRATEGY_ID = "11111111-2222-4333-8444-555555555555";
const BACKTEST_ID = "66666666-7777-4888-9999-aaaaaaaaaaaa";

function validPayload(overrides: Record<string, unknown> = {}) {
  return {
    version: ONBOARDING_VERSION,
    step: "welcome",
    strategyId: STRATEGY_ID,
    backtestId: BACKTEST_ID,
    startedAt: 1_725_000_000_000,
    ...overrides,
  };
}

describe("OnboardingPersistSchema", () => {
  it("유효한 persist payload를 통과시키고 다섯 키를 보존한다", () => {
    const payload = validPayload();
    const parsed = OnboardingPersistSchema.safeParse(payload);

    expect(parsed.success).toBe(true);
    if (!parsed.success) {
      return;
    }
    expect(parsed.data).toEqual(payload);
    expect(Object.keys(parsed.data)).toEqual([
      "version",
      "step",
      "strategyId",
      "backtestId",
      "startedAt",
    ]);
  });

  it("상위 버전 payload를 거부한다", () => {
    expect(
      OnboardingPersistSchema.safeParse(
        validPayload({ version: ONBOARDING_VERSION + 1 }),
      ).success,
    ).toBe(false);
  });

  it("하위 버전 payload를 거부한다", () => {
    expect(
      OnboardingPersistSchema.safeParse(
        validPayload({ version: ONBOARDING_VERSION - 1 }),
      ).success,
    ).toBe(false);
  });

  it.each(["welcome", "strategy", "backtest", "result"])(
    "%s step을 통과시킨다",
    (step) => {
      expect(OnboardingPersistSchema.safeParse(validPayload({ step })).success).toBe(
        true,
      );
    },
  );

  it.each(["done", "WELCOME", ""])("목록 밖 step %j을 거부한다", (step) => {
    expect(OnboardingPersistSchema.safeParse(validPayload({ step })).success).toBe(
      false,
    );
  });

  it("두 id의 null을 통과시킨다", () => {
    expect(
      OnboardingPersistSchema.safeParse(
        validPayload({ strategyId: null, backtestId: null }),
      ).success,
    ).toBe(true);
  });

  it.each(["strategyId", "backtestId"] as const)("비-UUID %s를 거부한다", (idKey) => {
    expect(
      OnboardingPersistSchema.safeParse(validPayload({ [idKey]: "not-a-uuid" }))
        .success,
    ).toBe(false);
  });

  it.each(["strategyId", "backtestId"] as const)("누락한 %s를 거부한다", (idKey) => {
    const payload = validPayload();
    delete payload[idKey];

    expect(OnboardingPersistSchema.safeParse(payload).success).toBe(false);
  });

  it("startedAt=0을 통과시킨다", () => {
    expect(OnboardingPersistSchema.safeParse(validPayload({ startedAt: 0 })).success).toBe(
      true,
    );
  });

  it.each([-1, 1.5, "123"])("유효하지 않은 startedAt %j를 거부한다", (startedAt) => {
    expect(
      OnboardingPersistSchema.safeParse(validPayload({ startedAt })).success,
    ).toBe(false);
  });

  it("여분 키를 strip하고 payload를 통과시킨다", () => {
    const parsed = OnboardingPersistSchema.safeParse(validPayload({ extra: 1 }));

    expect(parsed.success).toBe(true);
    if (!parsed.success) {
      return;
    }
    expect(parsed.data).not.toHaveProperty("extra");
  });

  it("두 schema가 safeParse를 제공하는 실제 Zod schema다", () => {
    expect(typeof OnboardingStepSchema.safeParse).toBe("function");
    expect(typeof OnboardingPersistSchema.safeParse).toBe("function");
  });
});
