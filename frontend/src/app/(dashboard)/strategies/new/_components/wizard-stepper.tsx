// Sprint 7c T4: 3-step Wizard stepper — completed / active / pending 3-state 시각화.
// Pass 6 Responsive: 모바일 세로 stack / 데스크탑 가로 정렬.

import { CheckIcon } from "lucide-react";

export function WizardStepper({ current }: { current: 1 | 2 | 3 }) {
  const steps = [
    { n: 1, label: "업로드 방식" },
    { n: 2, label: "코드 입력" },
    { n: 3, label: "확인" },
  ] as const;
  return (
    <nav
      className="flex flex-col md:flex-row items-start justify-between gap-2"
      aria-label="전략 생성 진행 단계"
    >
      {steps.map((s, i) => {
        const completed = s.n < current;
        const active = s.n === current;
        return (
          <div key={s.n} className="flex flex-1 flex-col items-center">
            <div className="flex w-full items-center">
              {i > 0 && (
                <div
                  className={
                    "h-0.5 flex-1 " +
                    (s.n <= current ? "bg-[color:var(--success)]" : "bg-[color:var(--border)]")
                  }
                />
              )}
              <div
                aria-current={active ? "step" : undefined}
                className={
                  "mx-2 grid size-10 place-items-center rounded-full border-2 font-mono text-sm font-semibold " +
                  (completed
                    ? "border-[color:var(--success)] bg-[color:var(--success)] text-white"
                    : active
                      ? "border-[color:var(--primary)] bg-[color:var(--primary)] text-white shadow-[0_0_0_4px_rgba(37,99,235,0.15)]"
                      : "border-[color:var(--border)] bg-white text-[color:var(--text-muted)]")
                }
              >
                {completed ? <CheckIcon className="size-4" /> : s.n}
              </div>
              {i < steps.length - 1 && (
                <div
                  className={
                    "h-0.5 flex-1 " +
                    (s.n < current ? "bg-[color:var(--success)]" : "bg-[color:var(--border)]")
                  }
                />
              )}
            </div>
            <p
              className={
                "mt-2 text-xs font-medium break-keep " +
                (active ? "text-[color:var(--primary)]" : "text-[color:var(--text-secondary)]")
              }
            >
              {s.label}
            </p>
          </div>
        );
      })}
    </nav>
  );
}
