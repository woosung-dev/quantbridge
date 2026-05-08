// 포지션 사이즈 슬라이더 — prototype 1:1 thumb/track + 자기자본 환산 표시 (Sprint 42-polish W4-fidelity)
"use client";

import type { CSSProperties } from "react";

export interface PositionSizeSliderProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  label?: string;
  /** 자기자본 환산 표시 (예: capital * value/100) — 미지정 시 미표시. */
  capitalUsd?: number | null;
}

function formatUsd(n: number): string {
  return Math.round(n).toLocaleString();
}

export function PositionSizeSlider({
  value,
  onChange,
  min = 1,
  max = 100,
  step = 1,
  unit = "%",
  label = "포지션 사이즈",
  capitalUsd = null,
}: PositionSizeSliderProps) {
  const equiv =
    capitalUsd != null && Number.isFinite(capitalUsd)
      ? Math.round((capitalUsd * value) / 100)
      : null;

  // prototype track 진행도 (linear-gradient background-size). min~max 범위를 0~100% 로 정규화.
  const span = max - min === 0 ? 1 : max - min;
  const progressPct = Math.max(0, Math.min(100, ((value - min) / span) * 100));

  return (
    <div
      className="flex flex-col gap-2.5"
      data-testid="position-size-slider-root"
    >
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium">{label}</span>
        <span
          className="font-mono text-[0.95rem] font-semibold text-[var(--primary)]"
          aria-live="polite"
          data-testid="position-size-slider-value"
        >
          {value}
          {unit}
          {equiv != null ? (
            <span className="ml-1.5 text-[0.8rem] font-normal text-muted-foreground">
              ≈ ${formatUsd(equiv)}
            </span>
          ) : null}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label={label}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        data-testid="position-size-slider-input"
        className="qb-range-slider"
        style={{ ["--qb-slider-progress" as string]: `${progressPct}%` } as CSSProperties}
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>
          {min}
          {unit}
        </span>
        <span>
          {max}
          {unit}
        </span>
      </div>
    </div>
  );
}
