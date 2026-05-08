// 온보딩 옵션 선택형 라디오 카드 — Sprint 42-polish W2-fidelity + Sprint 44 W F2
// docs/prototypes/05-onboarding.html `.option` (lines 304-385) 1:1 정합:
//  - 16px padding, 1.5px border (selected=primary 1.5px), radius var(--radius-md)
//  - hover: border-primary + bg-primary-light
//  - selected: border-primary + bg-primary-light + ring 0 0 0 3px rgba(37,99,235,.08)
//  - icon 40x40 circle, primary-light → primary on selected
//  - checkmark 22x22 circle, transparent → primary on selected
// Sprint 44 W F2: selected 시에도 미세 -translate-y 0.5px + ring-2 강화 (state 명확화)
// + active:translate-y-0 (press feedback)
"use client";

import { CheckIcon } from "lucide-react";
import type { KeyboardEvent, ReactNode } from "react";

export interface OptionCardRadioProps {
  value: string;
  label: string;
  description: string;
  icon: ReactNode;
  selected: boolean;
  onSelect: (value: string) => void;
  badge?: string;
}

export function OptionCardRadio({
  value,
  label,
  description,
  icon,
  selected,
  onSelect,
  badge,
}: OptionCardRadioProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      onSelect(value);
    }
  };

  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      data-value={value}
      data-selected={selected}
      data-testid={`option-card-${value}`}
      onClick={() => onSelect(value)}
      onKeyDown={handleKeyDown}
      className={[
        "flex w-full items-center gap-3 rounded-[var(--radius-md)] p-4 text-left",
        "transition-[border-color,background-color,box-shadow,transform] duration-200 ease-out",
        "border-[1.5px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--primary)]/35",
        "motion-safe:active:translate-y-0",
        selected
          // Sprint 44 W F2: selected 시 미세 -translate-y 0.5px + ring 두께 미세 강화
          ? "border-[color:var(--primary)] bg-[color:var(--primary-light)] shadow-[0_0_0_3px_rgba(37,99,235,0.08)] motion-safe:-translate-y-[0.5px]"
          : "border-[color:var(--border)] bg-[color:var(--card)] hover:border-[color:var(--primary)] hover:bg-[color:var(--primary-light)] motion-safe:hover:-translate-y-px motion-safe:hover:shadow-[0_4px_14px_rgba(15,23,42,0.06)]",
      ].join(" ")}
    >
      <span
        aria-hidden="true"
        className={[
          "grid h-10 w-10 shrink-0 place-items-center rounded-full transition-colors duration-200",
          selected
            ? "bg-[color:var(--primary)] text-white"
            : "bg-[color:var(--primary-light)] text-[color:var(--primary)]",
        ].join(" ")}
      >
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2 text-[0.95rem] font-semibold text-[color:var(--text-primary)]">
          {label}
          {badge ? (
            <span className="rounded-[10px] bg-[color:var(--success-light)] px-2 py-[2px] text-[0.68rem] font-semibold tracking-[0.02em] text-[color:var(--success)]">
              {badge}
            </span>
          ) : null}
        </span>
        <span className="mt-[2px] block text-[0.8rem] text-[color:var(--text-muted)]">
          {description}
        </span>
      </span>
      <span
        aria-hidden="true"
        className={[
          "grid h-[22px] w-[22px] shrink-0 place-items-center rounded-full border-2 transition-all duration-200",
          selected
            ? "border-[color:var(--primary)] bg-[color:var(--primary)] text-white"
            : "border-[color:var(--border)] bg-transparent text-transparent",
        ].join(" ")}
        data-testid={`option-card-check-${value}`}
      >
        <CheckIcon className="h-3 w-3" strokeWidth={3.5} />
      </span>
    </button>
  );
}
