// H2 Sprint 11 Phase D: Onboarding 4-step progress indicator.
// Sprint 7c wizard-stepper.tsx 패턴 승계 — completed / active / pending 3-state.
// 모바일: 세로 stack. 데스크톱: 가로 정렬.

import { CheckIcon } from "lucide-react";

import {
  ONBOARDING_STEPS,
  ONBOARDING_STEP_LABEL,
  type OnboardingStep,
} from "@/features/onboarding/types";

export function OnboardingStepper({ current }: { current: OnboardingStep }) {
  const currentIdx = ONBOARDING_STEPS.indexOf(current);
  return (
    <nav
      className="flex flex-col md:flex-row items-start justify-between gap-2"
      aria-label="온보딩 진행 단계"
    >
      {ONBOARDING_STEPS.map((stepKey, i) => {
        const completed = i < currentIdx;
        const active = i === currentIdx;
        const label = ONBOARDING_STEP_LABEL[stepKey];
        return (
          <div key={stepKey} className="flex flex-1 flex-col items-center">
            <div className="flex w-full items-center">
              {i > 0 && (
                <div
                  className={
                    "h-0.5 flex-1 " +
                    (i <= currentIdx
                      ? "bg-[color:var(--success)]"
                      : "bg-[color:var(--border)]")
                  }
                />
              )}
              <div
                aria-current={active ? "step" : undefined}
                data-testid={`onboarding-step-dot-${stepKey}`}
                className={
                  "mx-2 grid size-10 place-items-center rounded-full border-2 font-mono text-sm font-semibold " +
                  (completed
                    ? "border-[color:var(--success)] bg-[color:var(--success)] text-white"
                    : active
                      ? "border-[color:var(--primary)] bg-[color:var(--primary)] text-white shadow-[0_0_0_4px_rgba(37,99,235,0.15)]"
                      : "border-[color:var(--border)] bg-white text-[color:var(--text-muted)]")
                }
              >
                {completed ? <CheckIcon className="size-4" /> : i + 1}
              </div>
              {i < ONBOARDING_STEPS.length - 1 && (
                <div
                  className={
                    "h-0.5 flex-1 " +
                    (i < currentIdx
                      ? "bg-[color:var(--success)]"
                      : "bg-[color:var(--border)]")
                  }
                />
              )}
            </div>
            <p
              className={
                "mt-2 text-xs font-medium break-keep " +
                (active
                  ? "text-[color:var(--primary)]"
                  : "text-[color:var(--text-secondary)]")
              }
            >
              {label}
            </p>
          </div>
        );
      })}
    </nav>
  );
}
