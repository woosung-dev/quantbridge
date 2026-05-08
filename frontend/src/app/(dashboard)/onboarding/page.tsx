"use client";

// H2 Sprint 11 Phase D: Onboarding 4-step wizard shell.
// Clerk 인증은 (dashboard) layout + proxy.ts 에서 이미 보장.
// store.step 에 따라 conditional render. TTL 초과 시 mount 시점에 welcome 으로 reset.
//
// Selector 계약 (LESSON-004): scalar selector 만 사용.

import { useEffect } from "react";

import {
  maybeExpireAndReset,
  nextStep,
  prevStep,
  selectBacktestId,
  selectStep,
  selectStrategyId,
  useOnboardingStore,
} from "@/features/onboarding/store";
import { ONBOARDING_STEPS } from "@/features/onboarding/types";

import { IllustrationFrame } from "./_components/illustration-frame";
import { ProgressStepper } from "./_components/progress-stepper";
import { Step1Welcome } from "./_components/step-1-welcome";
import { Step2Strategy } from "./_components/step-2-strategy";
import { Step3Backtest } from "./_components/step-3-backtest";
import { Step4Result } from "./_components/step-4-result";

// 4단계 상수 — prototype 05-onboarding 의 라벨 승계.
const STEPPER_STEPS = [
  { id: 1, label: "환영" },
  { id: 2, label: "샘플 전략" },
  { id: 3, label: "백테스트" },
  { id: 4, label: "결과" },
] as const;

const STEP_ILLUSTRATION = {
  welcome: "code",
  strategy: "code",
  backtest: "chart",
  result: "complete",
} as const;

export default function OnboardingPage() {
  // scalar selectors — 객체 selector 금지 (LESSON-004).
  const step = useOnboardingStore(selectStep);
  const strategyId = useOnboardingStore(selectStrategyId);
  const backtestId = useOnboardingStore(selectBacktestId);

  // store actions 는 참조가 안정적 (zustand create 결과의 method).
  const setStep = useOnboardingStore((s) => s.setStep);
  const setStrategy = useOnboardingStore((s) => s.setStrategy);
  const setBacktest = useOnboardingStore((s) => s.setBacktest);
  const reset = useOnboardingStore((s) => s.reset);

  // 마운트 시 TTL 초과 체크 → 초과하면 welcome 으로 돌아감.
  useEffect(() => {
    maybeExpireAndReset();
  }, []);

  const handleNext = () => {
    setStep(nextStep(step));
  };
  const handleBack = () => {
    setStep(prevStep(step));
  };

  const handleStrategyReady = (newStrategyId: string) => {
    setStrategy(newStrategyId);
    setStep("backtest");
  };

  const handleBacktestReady = (newBacktestId: string) => {
    setBacktest(newBacktestId);
    setStep("result");
  };

  const handleFinish = () => {
    // 완료 후 store 를 비워서 재접근 시 welcome 부터 시작.
    reset();
  };

  // store enum (welcome/strategy/backtest/result) → 1-based numeric step.
  const currentStepNum = ONBOARDING_STEPS.indexOf(step) + 1;
  const illustrationVariant = STEP_ILLUSTRATION[step];

  return (
    <div className="mx-auto flex max-w-[720px] flex-col items-center px-4 py-10 md:py-12">
      <header className="mb-6 w-full text-center md:mb-8">
        <h1 className="font-display text-2xl font-bold tracking-tight md:text-[1.75rem]">
          온보딩
        </h1>
        <p className="mt-2 text-sm text-[color:var(--text-secondary)]">
          5분 안에 첫 Pine Script 백테스트를 완주해보세요.
        </p>
      </header>

      <ProgressStepper currentStep={currentStepNum} steps={STEPPER_STEPS} />

      <section
        data-testid="onboarding-step-panel"
        data-step={step}
        className="mt-10 grid w-full animate-[cardIn_350ms_ease-out_both] gap-6 rounded-[var(--radius-xl)] border border-[color:var(--border)] bg-[color:var(--card)] p-6 shadow-[var(--card-shadow)] md:grid-cols-2 md:gap-10 md:p-14"
      >
        <div className="hidden md:block">
          <IllustrationFrame variant={illustrationVariant} />
        </div>
        <div className="flex min-w-0 flex-col">
          {step === "welcome" && <Step1Welcome onNext={handleNext} />}
          {step === "strategy" && (
            <Step2Strategy
              onStrategyReady={handleStrategyReady}
              onBack={handleBack}
            />
          )}
          {step === "backtest" && (
            <Step3Backtest
              strategyId={strategyId}
              onBacktestReady={handleBacktestReady}
              onBack={handleBack}
            />
          )}
          {step === "result" && (
            <Step4Result backtestId={backtestId} onFinish={handleFinish} />
          )}
        </div>
      </section>
    </div>
  );
}
