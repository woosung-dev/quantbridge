// 404/500/503 에러 페이지 illustration — prototype 11 1:1 visual fidelity (큰 backdrop 코드 + 96px 원형 아이콘 SVG)

import type { JSX } from "react";

export type ErrorVariant = "404" | "500" | "503";

interface ErrorIllustrationProps {
  variant: ErrorVariant;
}

// variant 별 색조 — prototype 11 의 backdrop / icon-wrap 색상 매핑
const VARIANT_STYLES: Record<
  ErrorVariant,
  {
    backdropColor: string; // 큰 코드 글자 배경색 (200pt scale)
    iconBg: string; // 96px 원형 아이콘 배경 gradient
    sectionBg: string; // section 자체 radial gradient
    motion: string; // 아이콘 애니메이션 클래스 (motion-reduce 시 비활성)
  }
> = {
  "404": {
    backdropColor: "text-[color:var(--primary-light)]",
    iconBg:
      "bg-gradient-to-br from-[color:var(--primary-light)] to-[color:var(--primary-100)]",
    sectionBg:
      "bg-[radial-gradient(ellipse_at_top,_#EFF6FF_0%,_var(--bg)_60%)]",
    motion: "motion-safe:animate-[float_3.6s_ease-in-out_infinite]",
  },
  "500": {
    backdropColor: "text-[#FEE2E2]",
    iconBg:
      "bg-gradient-to-br from-[#FEF2F2] to-[color:var(--destructive-light)]",
    sectionBg:
      "bg-[radial-gradient(ellipse_at_top,_#FEF2F2_0%,_var(--bg)_60%)]",
    motion: "motion-safe:animate-pulse",
  },
  "503": {
    backdropColor: "text-[#FEF3C7]",
    iconBg:
      "bg-gradient-to-br from-[color:var(--primary-light)] to-[color:var(--primary-100)]",
    sectionBg:
      "bg-[radial-gradient(ellipse_at_top,_#F5F9FF_0%,_var(--bg)_60%)]",
    motion: "",
  },
};

// variant 별 SVG icon (56x56) — prototype 11 동일
const VARIANT_ICONS: Record<ErrorVariant, JSX.Element> = {
  "404": (
    // 기울어진 나침반 + 빨간 균열
    <svg width="56" height="56" viewBox="0 0 56 56" fill="none" aria-hidden="true">
      <g transform="rotate(-18 28 28)">
        <circle cx="28" cy="28" r="22" stroke="#2563EB" strokeWidth="2.5" fill="#EFF6FF" />
        <circle cx="28" cy="28" r="3" fill="#2563EB" />
        <path d="M28 10L32 28L28 28Z" fill="#2563EB" />
        <path d="M28 46L24 28L28 28Z" fill="#93C5FD" />
      </g>
      <path
        d="M14 12L24 26L20 32L34 46"
        stroke="#DC2626"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
  "500": (
    // 경고 삼각형
    <svg width="56" height="56" viewBox="0 0 56 56" fill="none" aria-hidden="true">
      <path
        d="M28 6L52 46H4L28 6Z"
        fill="#FEE2E2"
        stroke="#DC2626"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <line x1="28" y1="22" x2="28" y2="34" stroke="#DC2626" strokeWidth="3" strokeLinecap="round" />
      <circle cx="28" cy="40" r="2.5" fill="#DC2626" />
    </svg>
  ),
  "503": (
    // 톱니바퀴 (rotate-anim)
    <svg
      width="56"
      height="56"
      viewBox="0 0 56 56"
      fill="none"
      aria-hidden="true"
      className="motion-safe:animate-spin motion-safe:[animation-duration:4s]"
    >
      <circle cx="28" cy="28" r="12" fill="#DBEAFE" stroke="#2563EB" strokeWidth="2" />
      <circle cx="28" cy="28" r="4" fill="#2563EB" />
      <g fill="#2563EB">
        <rect x="26" y="10" width="4" height="5" rx="1" />
        <rect x="26" y="41" width="4" height="5" rx="1" />
        <rect x="10" y="26" width="5" height="4" rx="1" />
        <rect x="41" y="26" width="5" height="4" rx="1" />
        <rect x="14" y="14" width="5" height="4" rx="1" transform="rotate(45 16.5 16)" />
        <rect x="37" y="14" width="5" height="4" rx="1" transform="rotate(-45 39.5 16)" />
        <rect x="14" y="38" width="5" height="4" rx="1" transform="rotate(-45 16.5 40)" />
        <rect x="37" y="38" width="5" height="4" rx="1" transform="rotate(45 39.5 40)" />
      </g>
    </svg>
  ),
};

/**
 * 에러 페이지 illustration — prototype 11 의 큰 backdrop 코드 + 96px 원형 아이콘 + section background 묶음.
 *
 * 사용처: error.tsx (500), not-found.tsx (404), maintenance/page.tsx (503).
 *
 * 토큰: globals.css 의 --primary-light / --primary-100 / --destructive-light / --bg 사용. light theme 만 정의.
 */
export function ErrorIllustration({ variant }: ErrorIllustrationProps) {
  const styles = VARIANT_STYLES[variant];
  return (
    <>
      {/* 섹션 background gradient — 부모가 relative + overflow-hidden 일 때 효과 */}
      <div
        aria-hidden="true"
        data-testid="error-illustration-bg"
        data-variant={variant}
        className={`pointer-events-none absolute inset-0 z-0 ${styles.sectionBg}`}
      />
      {/* 큰 코드 backdrop — 200pt clamp(6rem, 15vw, 9rem) */}
      <div
        aria-hidden="true"
        data-testid="error-illustration-backdrop"
        className={`pointer-events-none absolute left-1/2 top-1/2 z-0 select-none font-display text-[clamp(6rem,15vw,9rem)] font-extrabold leading-[0.9] tracking-tight ${styles.backdropColor}`}
        style={{ transform: "translate(-50%, -58%)" }}
      >
        {variant}
      </div>
      {/* 96px 원형 아이콘 wrap */}
      <div
        data-testid="error-illustration-icon"
        className={`relative z-[2] mx-auto mb-6 grid h-24 w-24 place-items-center rounded-3xl shadow-lg ${styles.iconBg} ${styles.motion}`}
        aria-hidden="true"
      >
        {VARIANT_ICONS[variant]}
      </div>
    </>
  );
}
