"use client";

// 온보딩 4스텝 위저드 셸 (client) — C 디자인 언어 이식 (W3-E). page.tsx(server)가 렌더.
// 프로토타입 screen-12 의 .report/.ob-steps/.card 시맨틱을 소비하되, 스텝 흐름과 실데이터
// (실 strategyId/backtestId)는 그대로 둔다. 프로토타입은 결과 스텝 해설 화면이라 run_2f9c41
// 등 캐논 샘플값을 인쇄하지만, 라이브 위저드는 사용자 실 실행 ID 를 쓰므로 캐논 샘플 숫자는
// 옮기지 않는다(§4.9 스키마 미백업 값 미렌더).
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

import { IllustrationFrame } from "./illustration-frame";
import { ProgressStepper } from "./progress-stepper";
import { Step1Welcome } from "./step-1-welcome";
import { Step2Strategy } from "./step-2-strategy";
import { Step3Backtest } from "./step-3-backtest";
import { Step4Result } from "./step-4-result";

// 4단계 상수 — features/onboarding/types 의 ONBOARDING_STEP_LABEL 과 정합.
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

export function OnboardingView() {
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
    <main className="page">
      <div className="ob-wrap">
        {/* ===== 개요 헤더 ===== */}
        <section className="card rise d1" aria-label="온보딩 개요">
          <div className="report">
            <div>
              <h1 className="report-title">온보딩</h1>
              <p className="card-sub">5분 안에 첫 Pine Script 백테스트를 완주해보세요.</p>
              <div className="report-meta">
                {/* 프로토타입의 하드코딩 사용자명 칩(woosung)은 실 신원이 아니므로 재현하지
                    않는다(dashboard-sidebar 정직성 선례). 실 계정 표시는 셸의 Clerk
                    UserButton 이 담당하고, useUser 는 앱 어디에도 도입돼 있지 않다. */}
                <span className="chip">스텝 {currentStepNum} / 4</span>
                <span className="chip accent">바 단위 이벤트 루프</span>
              </div>
            </div>
          </div>
        </section>

        {/* ===== 진행 상태 ===== */}
        <section className="section rise d2" aria-label="온보딩 진행 상태">
          <div className="card">
            <ProgressStepper currentStep={currentStepNum} steps={STEPPER_STEPS} />
          </div>
        </section>

        {/* ===== 현재 단계 ===== */}
        <section
          className="section rise d3"
          data-testid="onboarding-step-panel"
          data-step={step}
          aria-label="현재 온보딩 단계"
        >
          <div className="card">
            <div className="card-body ob-panel">
              <div className="ob-illus">
                <IllustrationFrame variant={illustrationVariant} />
              </div>
              <div className="ob-step-content">
                {step === "welcome" && <Step1Welcome onNext={handleNext} />}
                {step === "strategy" && (
                  <Step2Strategy onStrategyReady={handleStrategyReady} onBack={handleBack} />
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
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
