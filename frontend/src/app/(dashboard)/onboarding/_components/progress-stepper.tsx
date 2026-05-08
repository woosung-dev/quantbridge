// 온보딩 4단계 진행 indicator — Sprint 42-polish W2
// Prototype 05-onboarding.html visual 승계: 원형 step + 연결선 (completed=실선/success, pending=dashed/border).
// active 단계는 primary glow + pulse animation (prefers-reduced-motion 시 자동 비활성).
//
// 기존 onboarding-stepper.tsx 와 별도 — prototype 의 폼 매치 + active pulse + dashed pending lines 적용.
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

export function ProgressStepper({ currentStep, steps }: ProgressStepperProps) {
  const total = steps.length;
  return (
    <nav
      role="progressbar"
      aria-valuenow={currentStep}
      aria-valuemin={1}
      aria-valuemax={total}
      aria-label="온보딩 진행 단계"
      className="w-full"
    >
      <p
        className="mb-3 text-center font-mono text-xs font-medium tracking-wide text-[color:var(--text-muted)]"
        aria-live="polite"
      >
        단계 {currentStep} / {total}
      </p>
      <ol className="flex w-full items-start gap-0">
        {steps.map((step, idx) => {
          const completed = step.id < currentStep;
          const active = step.id === currentStep;
          const showLine = idx < total - 1;
          const lineCompleted = step.id < currentStep;
          return (
            <li
              key={step.id}
              className="flex flex-1 flex-col items-center"
              data-step={step.id}
              data-state={completed ? "completed" : active ? "active" : "pending"}
            >
              <div className="flex w-full items-center">
                <div className="flex flex-1 justify-end">
                  {/* 좌측 padding (첫 step 은 빈 공간) */}
                </div>
                <div
                  data-testid={`progress-step-circle-${step.id}`}
                  className={[
                    "grid size-10 shrink-0 place-items-center rounded-full border-2 font-mono text-sm font-semibold transition-all duration-300",
                    completed
                      ? "border-[color:var(--success)] bg-[color:var(--success)] text-white"
                      : active
                        ? "border-[color:var(--primary)] bg-[color:var(--primary)] text-white shadow-[0_0_0_6px_var(--primary-light)] motion-safe:animate-pulse"
                        : "border-[color:var(--border)] bg-white text-[color:var(--text-muted)]",
                  ].join(" ")}
                  aria-hidden="true"
                >
                  {completed ? <CheckIcon className="size-4" /> : step.id}
                </div>
                {showLine ? (
                  <div
                    data-testid={`progress-step-line-${step.id}`}
                    className={[
                      "h-[2px] flex-1",
                      lineCompleted
                        ? "bg-[color:var(--success)]"
                        : "border-t-2 border-dashed border-[color:var(--border)] bg-transparent",
                    ].join(" ")}
                    aria-hidden="true"
                  />
                ) : (
                  <div className="flex-1" aria-hidden="true" />
                )}
              </div>
              <span
                className={[
                  "mt-2 hidden text-xs font-medium break-keep md:block",
                  completed
                    ? "text-[color:var(--success)] font-semibold"
                    : active
                      ? "text-[color:var(--primary)] font-semibold"
                      : "text-[color:var(--text-muted)]",
                ].join(" ")}
              >
                {step.label}
              </span>
              <span className="sr-only">
                {step.id}단계 {step.label}
                {completed ? ", 완료" : active ? ", 현재 단계" : ""}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
