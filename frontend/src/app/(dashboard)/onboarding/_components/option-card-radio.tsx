// 온보딩 옵션 선택형 라디오 카드 — Sprint 42-polish W2
// Prototype 05-onboarding.html `.option` 패턴 승계: icon + 텍스트 + checkmark.
// selected 시 border-primary + 그림자 ring + checkmark 표시. !selected hover 시 border-primary.
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
        "flex w-full items-center gap-3 rounded-[var(--radius-md)] border p-4 text-left transition-all duration-200 motion-safe:hover:translate-y-[-1px]",
        selected
          ? "border-2 border-[color:var(--primary)] bg-[color:var(--primary-light)] shadow-[0_0_0_3px_rgba(37,99,235,0.08)]"
          : "border border-[color:var(--border)] bg-[color:var(--card)] hover:border-[color:var(--primary)] hover:bg-[color:var(--primary-light)]",
      ].join(" ")}
    >
      <span
        aria-hidden="true"
        className={[
          "grid size-10 shrink-0 place-items-center rounded-full",
          selected
            ? "bg-[color:var(--primary)] text-white"
            : "bg-[color:var(--primary-light)] text-[color:var(--primary)]",
        ].join(" ")}
      >
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2 text-sm font-semibold text-[color:var(--text-primary)]">
          {label}
          {badge ? (
            <span className="rounded-[10px] bg-[color:var(--success-light)] px-2 py-[2px] text-[0.68rem] font-semibold tracking-wide text-[color:var(--success)]">
              {badge}
            </span>
          ) : null}
        </span>
        <span className="mt-[2px] block text-xs text-[color:var(--text-muted)]">
          {description}
        </span>
      </span>
      <span
        aria-hidden="true"
        className={[
          "grid size-[22px] shrink-0 place-items-center rounded-full border-2 transition-all duration-200",
          selected
            ? "border-[color:var(--primary)] bg-[color:var(--primary)] text-white"
            : "border-[color:var(--border)] bg-transparent text-transparent",
        ].join(" ")}
        data-testid={`option-card-check-${value}`}
      >
        <CheckIcon className="size-3" strokeWidth={3.5} />
      </span>
    </button>
  );
}
