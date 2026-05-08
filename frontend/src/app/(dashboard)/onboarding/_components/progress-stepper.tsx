// 온보딩 4단계 진행 indicator — Sprint 42-polish W2-fidelity + Sprint 44 W F2
// docs/prototypes/05-onboarding.html `.progress` (lines 167-236) 1:1 정합:
//  - circle 32px, font 0.875rem, completed=success, active=primary glow + pulse
//  - 연결선 top:15px center, completed=success solid 2px, pending=border dashed 2px
//  - 라벨 0.8rem, completed=success/600, active=primary/600, pending=text-muted/500
//
// 테스트 계약: circle.parentElement.parentElement = li (data-state). 체인 유지.
// Sprint 44 W F2: line transition duration 300ms (color/border smooth fill) + circle 300ms.
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
      className="mx-auto w-full max-w-[720px]"
    >
      <p
        className="mb-4 text-center font-mono text-[0.8rem] font-medium tracking-[0.02em] text-[color:var(--text-muted)]"
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
              className="flex flex-1 flex-col items-center gap-2.5"
              data-step={step.id}
              data-state={completed ? "completed" : active ? "active" : "pending"}
            >
              {/* circle + line row — circle.parentElement = 이 div, grandparent = li */}
              <div className="relative flex w-full items-center justify-center">
                <div
                  data-testid={`progress-step-circle-${step.id}`}
                  className={[
                    // Sprint 44 W F2: transition duration 300ms (250→300, fill 부드럽게)
                    "relative z-[2] grid h-8 w-8 shrink-0 place-items-center rounded-full border-2 font-mono text-[0.875rem] font-bold transition-all duration-300 ease-out",
                    completed
                      ? "border-[color:var(--success)] bg-[color:var(--success)] text-white"
                      : active
                        ? "border-[color:var(--primary)] bg-[color:var(--primary)] text-white shadow-[0_0_0_6px_var(--primary-light)] motion-safe:[animation:onb-step-pulse_2s_ease-in-out_infinite]"
                        : "border-[color:var(--border)] bg-white text-[color:var(--text-muted)]",
                  ].join(" ")}
                  aria-hidden="true"
                >
                  {completed ? <CheckIcon className="size-4" strokeWidth={3} /> : step.id}
                </div>
                {showLine ? (
                  <div
                    data-testid={`progress-step-line-${step.id}`}
                    className={[
                      // Sprint 44 W F2: line color transition 300ms (border-color, background-color)
                      "absolute left-1/2 top-1/2 z-[1] h-[2px] w-full -translate-y-1/2 transition-[background-color,border-color] duration-300 ease-out",
                      lineCompleted
                        ? "bg-[color:var(--success)]"
                        : "border-t-2 border-dashed border-[color:var(--border)] bg-transparent",
                    ].join(" ")}
                    aria-hidden="true"
                  />
                ) : null}
              </div>

              <span
                className={[
                  "hidden whitespace-nowrap text-[0.8rem] break-keep md:block",
                  completed
                    ? "font-semibold text-[color:var(--success)]"
                    : active
                      ? "font-semibold text-[color:var(--primary)]"
                      : "font-medium text-[color:var(--text-muted)]",
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
