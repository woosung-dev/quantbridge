// 법무 페이지 accent-amber callout — 중요 조항(법무 임시 고지 / 투자 위험 등) 강조 박스. Sprint 43 W14.

import type { ReactNode } from "react";

interface LegalCalloutProps {
  /** 박스 색조 — amber: 법무 임시본 / 위험 경고. info: 일반 안내. */
  tone?: "amber" | "info";
  /** 박스 좌상단 굵은 라벨 (예: "[법무 임시 — 법적 효력 제한적]"). */
  label?: string;
  /** 본문. 자유 ReactNode. */
  children: ReactNode;
}

/**
 * 법무 4 페이지 공통 강조 박스.
 *
 * - amber (default): 법무 임시 고지 / 투자 위험 / 지역 제한 등 주의 환기.
 * - info: 일반 부가 안내 (현재 미사용 reserved).
 *
 * 좌측 4px border + 14px padding + 14px font-size + 1.6 line-height.
 */
export function LegalCallout({ tone = "amber", label, children }: LegalCalloutProps) {
  const palette =
    tone === "amber"
      ? "border-amber-500 bg-amber-50 text-amber-900"
      : "border-blue-500 bg-blue-50 text-blue-900";

  return (
    <div
      data-testid="legal-callout"
      data-tone={tone}
      role="note"
      className={`rounded-md border-l-4 ${palette} p-4 text-[14px] leading-[1.6]`}
    >
      {label ? <strong className="font-semibold">{label}</strong> : null}{" "}
      {children}
    </div>
  );
}
