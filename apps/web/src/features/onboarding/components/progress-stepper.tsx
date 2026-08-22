// 온보딩 4스텝 진행 인디케이터 — C 디자인 언어 이식 (W3-E).
// 출처 docs/design/prototypes/shotgun-2026-07/screen-12-onboarding.html `.ob-steps` (1021-1082).
//  - 스텝 배지는 원형 금지, 반경 var(--r). 완료=중립+체크, 현재=코퍼, 대기=중립.
//  - 연결선은 ::before flex 라인. 768px 이하는 라벨을 접고 collapsed 요약을 노출.
//
// 테스트 계약(progress-stepper.test.tsx): `.ob-step-num`(data-testid) 의 부모의 부모 =
// li.ob-step[data-state]. role=progressbar + aria-valuenow/valuemax + "단계 N / 4" 텍스트.
"use client";

import { CheckIcon } from "lucide-react";

export interface ProgressStep {
  id: number;
  label: string;
}

export interface ProgressStepperProps {
  currentStep: number;
  steps: readonly ProgressStep[];
}

type StepState = "completed" | "active" | "pending";

// 각 상태의 단계 상태 라벨(프로토타입 ob-step-state 문구).
const STEP_STATE_LABEL: Record<StepState, string> = {
  completed: "완료",
  active: "진행 중",
  pending: "대기",
};

export function ProgressStepper({ currentStep, steps }: ProgressStepperProps) {
  const total = steps.length;
  const currentLabel = steps.find((s) => s.id === currentStep)?.label ?? "";
  return (
    <nav
      role="progressbar"
      aria-valuenow={currentStep}
      aria-valuemin={1}
      aria-valuemax={total}
      aria-label="온보딩 진행 단계"
    >
      <p className="ob-progress-count" aria-live="polite">
        단계 {currentStep} / {total}
      </p>
      <ol className="ob-steps" aria-label={`온보딩 ${total}스텝`}>
        {steps.map((step) => {
          const completed = step.id < currentStep;
          const active = step.id === currentStep;
          const state: StepState = completed ? "completed" : active ? "active" : "pending";
          const stepClass = `ob-step${completed ? " is-done" : active ? " is-current" : ""}`;
          return (
            <li
              key={step.id}
              className={stepClass}
              data-step={step.id}
              data-state={state}
              aria-current={active ? "step" : undefined}
              aria-label={`${step.id}단계 ${step.label}${
                completed ? ", 완료" : active ? ", 현재 단계" : ""
              }`}
            >
              {/* ob-step-num(circle) 의 부모 = ob-step-link, 조부모 = li. 테스트 체인 유지. */}
              <span className="ob-step-link">
                <span
                  className="ob-step-num"
                  data-testid={`progress-step-circle-${step.id}`}
                  aria-hidden="true"
                >
                  {completed ? <CheckIcon /> : step.id}
                </span>
                <span className="ob-step-text">
                  <span className="ob-step-title">{step.label}</span>
                  <span className="ob-step-state">{STEP_STATE_LABEL[state]}</span>
                </span>
              </span>
            </li>
          );
        })}
      </ol>
      <p className="ob-steps-collapsed">
        스텝 {currentStep} / {total} · {currentLabel}
      </p>
    </nav>
  );
}
