// 백테스트 기간 preset pills — 1M/3M/6M/1Y/3Y/5Y radiogroup
"use client";

import { cn } from "@/lib/utils";

export type DatePreset = "1m" | "3m" | "6m" | "1y" | "3y" | "5y" | "custom";

export interface DateRange {
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
}

interface PresetMeta {
  key: DatePreset;
  label: string;
  months: number | null; // null = custom
}

const PRESETS: readonly PresetMeta[] = [
  { key: "1m", label: "1M", months: 1 },
  { key: "3m", label: "3M", months: 3 },
  { key: "6m", label: "6M", months: 6 },
  { key: "1y", label: "1Y", months: 12 },
  { key: "3y", label: "3Y", months: 36 },
  { key: "5y", label: "5Y", months: 60 },
] as const;

function toYmd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// preset 키 → 현재 시각 기준 startDate / endDate 계산.
// endDate = 어제 (오늘 미완성 일봉 회피, BL-167 정합).
export function calcDateRange(preset: DatePreset): DateRange | null {
  if (preset === "custom") return null;
  const meta = PRESETS.find((p) => p.key === preset);
  if (!meta || meta.months == null) return null;
  const end = new Date();
  end.setDate(end.getDate() - 1);
  const start = new Date(end);
  start.setMonth(start.getMonth() - meta.months);
  return { startDate: toYmd(start), endDate: toYmd(end) };
}

export interface DatePresetPillsProps {
  value: DatePreset;
  onSelect: (preset: DatePreset, range: DateRange | null) => void;
}

export function DatePresetPills({ value, onSelect }: DatePresetPillsProps) {
  return (
    <div
      role="radiogroup"
      aria-label="기간 프리셋"
      className="flex flex-wrap gap-2"
      data-testid="date-preset-pills"
    >
      {PRESETS.map((p) => {
        const isActive = value === p.key;
        return (
          <button
            key={p.key}
            type="button"
            role="radio"
            aria-checked={isActive}
            data-testid={`date-preset-${p.key}`}
            onClick={() => onSelect(p.key, calcDateRange(p.key))}
            className={cn(
              "h-8 rounded-full border px-3 text-xs font-medium transition-colors",
              isActive
                ? "border-[var(--primary)] bg-[var(--primary)] text-white"
                : "border-[var(--border)] bg-transparent text-[var(--text-secondary)] hover:border-[var(--border-dark)]",
            )}
          >
            {p.label}
          </button>
        );
      })}
      <button
        type="button"
        role="radio"
        aria-checked={value === "custom"}
        data-testid="date-preset-custom"
        onClick={() => onSelect("custom", null)}
        className={cn(
          "h-8 rounded-full border px-3 text-xs font-medium transition-colors",
          value === "custom"
            ? "border-[var(--primary)] bg-[var(--primary)] text-white"
            : "border-[var(--border)] bg-transparent text-[var(--text-secondary)] hover:border-[var(--border-dark)]",
        )}
      >
        커스텀
      </button>
    </div>
  );
}
