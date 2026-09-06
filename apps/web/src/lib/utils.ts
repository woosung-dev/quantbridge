// Tailwind 클래스 병합(cn) 등 프로젝트 전역 유틸리티 모음.
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// shadcn/ui 표준 cn 헬퍼 — Tailwind 클래스 병합 + 충돌 해결
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
