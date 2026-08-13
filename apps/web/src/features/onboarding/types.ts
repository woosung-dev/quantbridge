// H2 Sprint 11 Phase D: Onboarding 4-step wizard 상태 타입.
// Step 전환은 store.setStep 을 통해서만 수행 — scalar selector 계약 (LESSON-004).

export type OnboardingStep = "welcome" | "strategy" | "backtest" | "result";

export const ONBOARDING_STEPS: readonly OnboardingStep[] = [
  "welcome",
  "strategy",
  "backtest",
  "result",
] as const;

// UI 표시용 라벨 (i18n 전 단계 — 한국어 고정).
export const ONBOARDING_STEP_LABEL: Record<OnboardingStep, string> = {
  welcome: "환영",
  strategy: "샘플 전략",
  backtest: "백테스트",
  result: "결과",
};

// 진행도 저장소 버전 — schemas.ts 와 동일 상수.
export const ONBOARDING_VERSION = 1;

// 5분 TTL — 이후 localStorage 복원 시 welcome 으로 reset (새 유저 경험 일관성).
export const ONBOARDING_TTL_MS = 5 * 60 * 1000;
