// H2 Sprint 11 Phase D: Onboarding 진행도 persist 스키마.
// zustand persist middleware 의 rehydrate 단계에서 이 스키마로 runtime 검증.

import { z } from "zod/v4";

import { ONBOARDING_VERSION } from "./types";

export const OnboardingStepSchema = z.enum([
  "welcome",
  "strategy",
  "backtest",
  "result",
]);

// persist payload — 버전 mismatch 시 reset.
export const OnboardingPersistSchema = z.object({
  version: z.literal(ONBOARDING_VERSION),
  step: OnboardingStepSchema,
  strategyId: z.uuid().nullable(),
  backtestId: z.uuid().nullable(),
  startedAt: z.number().int().nonnegative(),
});
export type OnboardingPersist = z.infer<typeof OnboardingPersistSchema>;
