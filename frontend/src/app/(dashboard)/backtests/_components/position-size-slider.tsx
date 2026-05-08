// 포지션 사이즈 슬라이더 — 실시간 값 표시 (native range, mobile touch 친화)
"use client";

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

  return (
    <div
      className="flex flex-col gap-2"
      data-testid="position-size-slider-root"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{label}</span>
        <span
          className="font-mono text-base font-medium text-[var(--primary)]"
          aria-live="polite"
          data-testid="position-size-slider-value"
        >
          {value}
          {unit}
          {equiv != null ? (
            <span className="ml-2 text-xs font-normal text-muted-foreground">
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
        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-muted accent-[var(--primary)]"
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
