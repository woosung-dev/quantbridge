// Tailwind 클래스 병합(cn) · 퍼센트 문자열 포맷팅(formatPercent) 등 프로젝트 전역 유틸리티 모음.
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// shadcn/ui 표준 cn 헬퍼 — Tailwind 클래스 병합 + 충돌 해결
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatPercent(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}
