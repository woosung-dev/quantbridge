// 온보딩 옵션 선택형 라디오 카드 — C 디자인 언어 이식 (W3-E).
// 반경 var(--r)(원형 배지는 프로토타입 없음). 선택 시 코퍼 테두리 + 코퍼-소프트 배경.
// 자체 focus ring 은 제거하고 전역 카퍼 :focus-visible(globals.css) 을 소비한다
// (운영 계약 §1-2 이중 링 해소). 반경 리터럴 rounded-[10px] → var(--r) 로 래칫 하강.
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
        "flex w-full items-center gap-3 rounded-[var(--r)] border-[1.5px] p-4 text-left",
        "transition-[border-color,background-color,transform] duration-200 ease-out",
        selected
          ? "border-[color:var(--copper)] bg-[color:var(--copper-soft)]"
          : "border-[color:var(--line)] bg-[color:var(--card-2)] hover:border-[color:var(--copper)] hover:bg-[color:var(--copper-soft)]",
      ].join(" ")}
    >
      <span
        aria-hidden="true"
        className={[
          "grid h-10 w-10 shrink-0 place-items-center rounded-[var(--r)] transition-colors duration-200",
          selected
            ? "bg-[color:var(--copper)] text-[color:var(--copper-ink)]"
            : "bg-[color:var(--copper-soft)] text-[color:var(--copper)]",
        ].join(" ")}
      >
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2 text-[0.95rem] font-semibold text-[color:var(--ink)]">
          {label}
          {badge ? (
            <span className="rounded-[var(--r)] border border-[color:var(--copper-line)] bg-[color:var(--copper-soft)] px-2 py-[2px] text-[0.68rem] font-semibold tracking-[0.02em] text-[color:var(--copper)]">
              {badge}
            </span>
          ) : null}
        </span>
        <span className="mt-[2px] block text-[0.8rem] text-[color:var(--ink-3)]">
          {description}
        </span>
      </span>
      <span
        aria-hidden="true"
        className={[
          "grid h-[22px] w-[22px] shrink-0 place-items-center rounded-[var(--r)] border-2 transition-all duration-200",
          selected
            ? "border-[color:var(--copper)] bg-[color:var(--copper)] text-[color:var(--copper-ink)]"
            : "border-[color:var(--line)] bg-transparent text-transparent",
        ].join(" ")}
        data-testid={`option-card-check-${value}`}
      >
        <CheckIcon className="h-3 w-3" strokeWidth={3.5} />
      </span>
    </button>
  );
}
