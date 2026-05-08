// 파라미터 슬라이더 (Position Size 등) — prototype 01 의 .slider-wrap 패턴 1:1 (Sprint 43 W9-fidelity)
// W4 의 position-size-slider.tsx 차용 + edit page 의 horizontal compact 형태 (label + slider + 값)
"use client";

import type { CSSProperties } from "react";

export interface ParameterSliderProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  ariaLabel?: string;
}

export function ParameterSlider({
  label,
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  unit = "%",
  ariaLabel,
}: ParameterSliderProps) {
  const span = max - min === 0 ? 1 : max - min;
  const progressPct = Math.max(0, Math.min(100, ((value - min) / span) * 100));

  return (
    <div
      className="flex items-center justify-between gap-3 border-b border-dashed border-[color:var(--border)] py-3 last:border-b-0 last:pb-0 first:pt-0"
      data-testid="parameter-slider-row"
    >
      <span className="shrink-0 text-[0.8125rem] font-medium text-[color:var(--text-secondary)]">
        {label}
      </span>
      <div className="flex max-w-[180px] flex-1 items-center gap-2.5">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-label={ariaLabel ?? label}
          aria-valuemin={min}
          aria-valuemax={max}
          aria-valuenow={value}
          className="qb-range-slider flex-1"
          data-testid="parameter-slider-input"
          style={{ ["--qb-slider-progress" as string]: `${progressPct}%` } as CSSProperties}
        />
        <span
          className="min-w-[34px] text-right font-mono text-[0.8125rem] font-semibold text-[color:var(--primary)]"
          aria-live="polite"
          data-testid="parameter-slider-value"
        >
          {value}
          {unit}
        </span>
      </div>
    </div>
  );
}
