"use client";

// H2 Sprint 11 Phase D: Onboarding wizard 진행도 Zustand store.
// persist middleware 로 localStorage 에 저장 (key: "qb-onboarding-v1").
//
// Selector 계약 (LESSON-004):
// - 반드시 scalar selector (`useOnboardingStore(s => s.step)`) 로만 구독.
// - 객체 selector / 전체 store 를 deps 로 넣으면 매 render 새 참조가 생겨
//   useEffect 가 무한 루프(CPU 100%)를 유발한다.
//
// TTL 정책 (5 분):
// - setStep/setStrategy/setBacktest 는 startedAt 을 유지 (세션 수명 측정).
// - 페이지 마운트 시 `maybeExpire()` 로 TTL 초과 여부를 확인하고,
//   초과 시 reset() 을 호출해 welcome 으로 돌아간다.
// - 5 분은 "5 분 내 첫 Pine 백테스트" 목표와 일치 — 초과 시 Fresh start 가
//   더 좋은 UX.

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import {
  ONBOARDING_STEPS,
  ONBOARDING_TTL_MS,
  ONBOARDING_VERSION,
  type OnboardingStep,
} from "./types";

export interface OnboardingState {
  step: OnboardingStep;
  strategyId: string | null;
  backtestId: string | null;
  startedAt: number;
  setStep: (step: OnboardingStep) => void;
  setStrategy: (strategyId: string) => void;
  setBacktest: (backtestId: string) => void;
  reset: () => void;
}

const STORAGE_KEY = "qb-onboarding-v1";

// 초기 상태 팩토리 — 테스트에서도 재사용.
// NOTE: startedAt 을 create 시점에 한 번 찍으면 SSR 과 hydrate 불일치가 생길 수 있어
// 0 으로 초기화하고, 첫 setStep/setStrategy/setBacktest 호출 시 실시간 Date.now() 로 채운다.
export function createInitialState(): Pick<
  OnboardingState,
  "step" | "strategyId" | "backtestId" | "startedAt"
> {
  return {
    step: "welcome",
    strategyId: null,
    backtestId: null,
    startedAt: 0,
  };
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set, get) => ({
      ...createInitialState(),
      setStep: (step) =>
        set((s) => ({
          step,
          startedAt: s.startedAt === 0 ? Date.now() : s.startedAt,
        })),
      setStrategy: (strategyId) =>
        set((s) => ({
          strategyId,
          startedAt: s.startedAt === 0 ? Date.now() : s.startedAt,
        })),
      setBacktest: (backtestId) =>
        set((s) => ({
          backtestId,
          startedAt: s.startedAt === 0 ? Date.now() : s.startedAt,
        })),
      reset: () => {
        void get; // keep get referenced for parity with zustand types
        set(createInitialState());
      },
    }),
    {
      name: STORAGE_KEY,
      version: ONBOARDING_VERSION,
      storage: createJSONStorage(() => {
        // SSR 시에는 localStorage 미접근 — in-memory no-op 폴백.
        if (typeof window === "undefined") {
          const memory = new Map<string, string>();
          return {
            getItem: (key) => memory.get(key) ?? null,
            setItem: (key, value) => {
              memory.set(key, value);
            },
            removeItem: (key) => {
              memory.delete(key);
            },
          };
        }
        return window.localStorage;
      }),
      partialize: (s) => ({
        step: s.step,
        strategyId: s.strategyId,
        backtestId: s.backtestId,
        startedAt: s.startedAt,
      }),
    },
  ),
);

// --- scalar selectors ---------------------------------------------------

export const selectStep = (s: OnboardingState): OnboardingStep => s.step;
export const selectStrategyId = (s: OnboardingState): string | null =>
  s.strategyId;
export const selectBacktestId = (s: OnboardingState): string | null =>
  s.backtestId;
export const selectStartedAt = (s: OnboardingState): number => s.startedAt;

// --- TTL helpers (pure, testable without React) --------------------------

export function isExpired(
  startedAt: number,
  now: number = Date.now(),
  ttlMs: number = ONBOARDING_TTL_MS,
): boolean {
  if (startedAt === 0) return false;
  return now - startedAt > ttlMs;
}

// 페이지 마운트 시 호출해서 TTL 초과면 자동 reset.
// returns true if expired-and-reset.
export function maybeExpireAndReset(now: number = Date.now()): boolean {
  const s = useOnboardingStore.getState();
  if (isExpired(s.startedAt, now)) {
    s.reset();
    return true;
  }
  return false;
}

// --- step navigation helper ---------------------------------------------

export function nextStep(step: OnboardingStep): OnboardingStep {
  const idx = ONBOARDING_STEPS.indexOf(step);
  if (idx < 0 || idx === ONBOARDING_STEPS.length - 1) return step;
  const next = ONBOARDING_STEPS[idx + 1];
  return next ?? step;
}

export function prevStep(step: OnboardingStep): OnboardingStep {
  const idx = ONBOARDING_STEPS.indexOf(step);
  if (idx <= 0) return step;
  const prev = ONBOARDING_STEPS[idx - 1];
  return prev ?? step;
}
