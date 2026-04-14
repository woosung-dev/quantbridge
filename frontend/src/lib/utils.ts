import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// shadcn/ui 표준 cn 헬퍼 — Tailwind 클래스 병합 + 충돌 해결
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

// 금융 숫자 포맷팅 — JetBrains Mono + tabular-nums 과 함께 사용
export function formatDecimal(
  value: number | string,
  options: { digits?: number; sign?: boolean } = {},
): string {
  const { digits = 2, sign = false } = options;
  const num = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(num)) return "-";
  const formatted = num.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return sign && num > 0 ? `+${formatted}` : formatted;
}

export function formatPercent(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}
