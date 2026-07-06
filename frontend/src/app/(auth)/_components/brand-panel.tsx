// 인증 페이지 좌측 카본 브랜드 패널 — Precision Instrument W5 PR-12
// 항상 다크(카본+코퍼): `dark` 클래스 스코프로 .dark 토큰을 고정 적용 (하드코딩 hex 금지).
// 카피/testid 불변 — 스타일만 v3 정합 (구 블루 그라디언트/글래스/글로우 폐기).

import Link from "next/link";
import { TickRuler } from "@/components/tick-ruler";

type BrandMode = "sign-in" | "sign-up";

interface BrandPanelProps {
  mode: BrandMode;
}

interface ModeCopy {
  heading: string;
  sub: string;
  testimonialText: string;
  testimonialAuthor: string;
  testimonialRole: string;
}

// Multi-Agent QA BL-271 fix (Sprint 60 S2) — 가짜 testimonial author 익명화 + sub 정직 표시
const MODE_COPY: Record<BrandMode, ModeCopy> = {
  "sign-in": {
    heading: "Pine Script 전략을\n실전 수익으로",
    sub: "Beta 단계 — 초기 사용자와 함께 만드는 퀀트 트레이딩 플랫폼",
    testimonialText: "backtest에서 최적화까지 3분이면 끝난다",
    testimonialAuthor: "초기 사용자",
    testimonialRole: "Beta dogfooder",
  },
  "sign-up": {
    heading: "지금 시작하세요\n무료 데모로 안전하게",
    sub: "가입 즉시 Bybit Demo 환경에서 전략을 검증할 수 있습니다",
    testimonialText: "회원가입 5분이면 첫 백테스트 결과를 본다",
    testimonialAuthor: "초기 사용자",
    testimonialRole: "Beta dogfooder",
  },
};

interface StatRow {
  value: string;
  label: string;
}

const STATS: StatRow[] = [
  { value: "Beta", label: "단계" },
  { value: "Dev", label: "환경" },
  { value: "Demo", label: "거래소" },
  { value: "Open", label: "feedback" },
];

// 5 사용자 avatar (initials + 플랫 시맨틱 액센트 — v3 그라디언트 폐기). hidden md+ 전용.
interface Avatar {
  initials: string;
  background: string;
}

const AVATARS: Avatar[] = [
  { initials: "JK", background: "var(--primary)" },
  { initials: "MH", background: "var(--bullish)" },
  { initials: "YS", background: "var(--bearish)" },
  { initials: "DW", background: "var(--chart-compare)" },
  { initials: "SJ", background: "var(--warning)" },
];

export function BrandPanel({ mode }: BrandPanelProps) {
  const copy = MODE_COPY[mode];

  return (
    <aside
      aria-label="QuantBridge 소개"
      className="dark relative hidden flex-col justify-between gap-12 overflow-hidden border-r border-[color:var(--border)] bg-[color:var(--bg)] p-16 text-[color:var(--text-primary)] md:flex"
    >
      {/* 로고 — fadeInUp 0.6s. 플랫 스틸 마크 (글래스/backdrop-blur 폐기) */}
      <Link
        href="/"
        aria-label="QuantBridge 홈으로 이동"
        className="auth-fade-in-1 relative inline-flex items-center gap-3 self-start"
      >
        <span
          aria-hidden="true"
          className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] border border-[color:var(--border-dark)] bg-[color:var(--card)]"
        >
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M3 17h18M5 17V9a2 2 0 012-2h2M19 17V9a2 2 0 00-2-2h-2M9 7V4M15 7V4M3 21h18"
              className="stroke-[color:var(--text-primary)]"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M9 11h6"
              className="stroke-[color:var(--primary)]"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>
        </span>
        <span className="qb-display-wide text-xl font-bold tracking-tight">
          QuantBridge
        </span>
      </Link>

      {/* 미들: 가치 제안 + 소셜 프루프 — fadeInUp 0.7s delay 0.1s */}
      <div className="auth-fade-in-2 relative flex flex-col gap-10">
        <div>
          <h1 className="m-0 whitespace-pre-line text-[2.5rem] leading-[1.2] font-bold">
            {copy.heading}
          </h1>
          <p className="mt-4 text-[1.05rem] leading-[1.6] text-[color:var(--text-secondary)]">
            {copy.sub}
          </p>
        </div>

        {/* 소셜 프루프 카드 — 플랫 스틸 카드: 1px 보더가 주인공 (글래스/blur 폐기) */}
        <div
          role="group"
          aria-label="사용자 현황"
          className="rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-[color:var(--card)] p-6"
        >
          {/* avatars row — 5 flat accent chips, -8px overlap, mb=14px */}
          <div
            aria-hidden="true"
            data-testid="brand-avatars"
            className="mb-[14px] flex items-center"
          >
            {AVATARS.map((av, idx) => (
              <span
                key={av.initials}
                className="font-display flex h-10 w-10 items-center justify-center rounded-full border-2 border-[color:var(--card)] text-[0.82rem] font-bold text-[color:var(--background)]"
                style={{
                  background: av.background,
                  marginLeft: idx === 0 ? 0 : "-8px",
                }}
              >
                {av.initials}
              </span>
            ))}
          </div>

          {/* live indicator — livePulse keyframe 유지, green 은 --success 토큰 */}
          <div className="flex items-center gap-2.5 text-[0.92rem] font-medium text-[color:var(--text-secondary)]">
            <span
              aria-hidden="true"
              className="relative inline-block h-2 w-2 flex-shrink-0 rounded-full bg-[color:var(--success)]"
            >
              <span
                aria-hidden="true"
                className="absolute -inset-1 rounded-full bg-[color:var(--success)]/50 motion-safe:animate-[livePulse_2s_infinite]"
              />
            </span>
            <span>
              Beta 단계 — 초기 사용자와 함께 검증 중
            </span>
          </div>

          {/* 시그니처 — 키 스탯 스트립 상단 계측 눈금 (DESIGN.md §0.1 공인 사이트) */}
          <TickRuler className="mt-[18px] opacity-70" />
          <div className="mt-3 grid grid-cols-2 gap-x-5 gap-y-3">
            {STATS.map((stat) => (
              <div
                key={stat.label}
                className="flex items-baseline gap-2 text-[0.82rem] text-[color:var(--text-secondary)]"
              >
                <span
                  className="font-semibold text-[color:var(--text-primary)]"
                  data-type="number"
                >
                  {stat.value}
                </span>
                <span className="text-[0.75rem] text-[color:var(--text-muted)]">
                  {stat.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 인용문 — fadeInUp 0.8s delay 0.2s */}
      <blockquote className="auth-fade-in-3 relative pl-7">
        <svg
          aria-hidden="true"
          className="absolute -top-2.5 -left-1 opacity-20"
          width="36"
          height="28"
          viewBox="0 0 36 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M0 28V18.666c0-3.111.51-5.935 1.528-8.47C2.546 7.66 4.08 5.333 6.132 3.2 8.183 1.066 10.74.066 13.8 0v5.066c-2.037.8-3.6 2.4-4.69 4.8-1.09 2.4-1.528 4.933-1.313 7.6H13.8V28H0zm20.1 0V18.666c0-3.111.51-5.935 1.528-8.47 1.018-2.535 2.552-4.862 4.604-6.996C28.283 1.066 30.84.066 33.9 0v5.066c-2.037.8-3.6 2.4-4.69 4.8-1.09 2.4-1.528 4.933-1.313 7.6H33.9V28H20.1z"
            fill="currentColor"
          />
        </svg>
        <p className="font-display m-0 mb-2.5 text-[1.05rem] leading-[1.55] font-medium">
          {copy.testimonialText}
        </p>
        <p className="text-[0.85rem] text-[color:var(--text-muted)]">
          <strong className="font-semibold text-[color:var(--text-secondary)]">
            {copy.testimonialAuthor}
          </strong>{" "}
          — {copy.testimonialRole}
        </p>
      </blockquote>
    </aside>
  );
}
