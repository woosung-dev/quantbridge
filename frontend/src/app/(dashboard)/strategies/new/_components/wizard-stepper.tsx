// 전략 생성 3단계 stepper — Sprint 42-polish W3 (prototype 07 매칭)
// completed (체크 아이콘 + success 색) / active (primary + pulseRing) / pending (dashed) 3-state
// completed↔active 사이 실선 (success), active↔pending 사이 dashed
// prefers-reduced-motion: pulseRing animation disable (motion-safe:)

import { CheckIcon } from "lucide-react";

interface WizardStep {
  n: 1 | 2 | 3;
  label: string;
}

const STEPS: readonly WizardStep[] = [
  { n: 1, label: "업로드 방식" },
  { n: 2, label: "코드 입력" },
  { n: 3, label: "확인" },
] as const;

export function WizardStepper({ current }: { current: 1 | 2 | 3 }) {
  return (
    <nav
      aria-label="전략 생성 진행 단계"
      className="mx-auto flex max-w-[600px] items-start justify-between"
    >
      {STEPS.map((step, idx) => {
        const completed = step.n < current;
        const active = step.n === current;
        const isLast = idx === STEPS.length - 1;

        return (
          <div key={step.n} className="flex flex-1 items-start">
            <StepNode n={step.n} label={step.label} completed={completed} active={active} />
            {!isLast && <StepLine completed={completed} />}
          </div>
        );
      })}
    </nav>
  );
}

function StepNode({
  n,
  label,
  completed,
  active,
}: {
  n: 1 | 2 | 3;
  label: string;
  completed: boolean;
  active: boolean;
}) {
  const status = completed ? "완료" : active ? "진행 중" : "대기";

  return (
    <div className="relative z-10 flex flex-col items-center gap-2">
      <div
        aria-current={active ? "step" : undefined}
        aria-label={`${n}단계 ${status}`}
        className={
          "grid size-10 place-items-center rounded-full font-mono text-sm font-bold transition-all " +
          (completed
            ? "border-2 border-[color:var(--success)] bg-[color:var(--success)] text-white"
            : active
              ? "border-2 border-[color:var(--primary)] bg-[color:var(--primary)] text-white shadow-[0_0_0_4px_rgba(37,99,235,0.15)] motion-safe:animate-[pulseRing_2.4s_ease-out_infinite]"
              : "border-2 border-dashed border-[color:var(--border-dark,#cbd5e1)] bg-white text-[color:var(--text-muted)]")
        }
      >
        {completed ? <CheckIcon className="size-4" strokeWidth={3} /> : n}
      </div>
      <p
        className={
          "break-keep text-xs font-semibold " +
          (active
            ? "text-[color:var(--primary)]"
            : completed
              ? "text-[color:var(--text-primary)]"
              : "text-[color:var(--text-secondary)]")
        }
      >
        {label}
      </p>
      <p
        className={
          "text-[0.65rem] font-medium " +
          (active
            ? "text-[color:var(--primary)]"
            : completed
              ? "text-[color:var(--success)]"
              : "text-[color:var(--text-muted)]")
        }
      >
        {status}
      </p>
    </div>
  );
}

function StepLine({ completed }: { completed: boolean }) {
  return (
    <div
      aria-hidden
      className={
        "mt-5 h-0.5 flex-1 " +
        (completed
          ? "bg-[color:var(--success)]"
          : "border-t-2 border-dashed border-[color:var(--border-dark,#cbd5e1)] bg-transparent")
      }
    />
  );
}
