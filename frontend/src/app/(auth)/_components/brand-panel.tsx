// 인증 페이지 좌측 다크 브랜드 패널 — Sprint 42-polish W1
// design source: docs/prototypes/04-login.html

import Link from "next/link";

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

const MODE_COPY: Record<BrandMode, ModeCopy> = {
  "sign-in": {
    heading: "Pine Script 전략을\n실전 수익으로",
    sub: "10,000+ 트레이더가 선택한 퀀트 트레이딩 플랫폼",
    testimonialText: "backtest에서 최적화까지 3분이면 끝난다",
    testimonialAuthor: "김지훈",
    testimonialRole: "Pro 트레이더",
  },
  "sign-up": {
    heading: "지금 시작하세요\n무료 데모로 안전하게",
    sub: "가입 즉시 Bybit Demo 환경에서 전략을 검증할 수 있습니다",
    testimonialText: "회원가입 5분이면 첫 백테스트 결과를 본다",
    testimonialAuthor: "박민하",
    testimonialRole: "Beta 사용자",
  },
};

interface StatRow {
  value: string;
  label: string;
}

const STATS: StatRow[] = [
  { value: "99.97%", label: "업타임" },
  { value: "<35ms", label: "체결" },
  { value: "156", label: "거래소" },
  { value: "2.4B", label: "거래량" },
];

export function BrandPanel({ mode }: BrandPanelProps) {
  const copy = MODE_COPY[mode];

  return (
    <aside
      aria-label="QuantBridge 소개"
      className="relative hidden flex-col justify-between gap-12 overflow-hidden p-16 text-white md:flex"
      style={{
        background:
          "linear-gradient(135deg, #1E293B 0%, #0F172A 50%, #1E40AF 100%)",
      }}
    >
      {/* 배경 장식 (radial gradient blobs) */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-[200px] -right-[200px] h-[600px] w-[600px]"
        style={{
          background:
            "radial-gradient(circle, rgba(37,99,235,0.25), transparent 70%)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-[150px] -left-[150px] h-[500px] w-[500px]"
        style={{
          background:
            "radial-gradient(circle, rgba(37,99,235,0.18), transparent 70%)",
        }}
      />

      {/* 로고 */}
      <Link
        href="/"
        aria-label="QuantBridge 홈으로 이동"
        className="relative inline-flex items-center gap-3"
      >
        <span
          aria-hidden="true"
          className="flex h-10 w-10 items-center justify-center rounded-[10px] border border-white/10 bg-white/5 backdrop-blur"
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
              stroke="#fff"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M9 11h6"
              stroke="#60A5FA"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>
        </span>
        <span
          className="text-xl font-extrabold tracking-tight text-white"
          style={{ fontFamily: "var(--font-display)" }}
        >
          QuantBridge
        </span>
      </Link>

      {/* 미들: 가치 제안 + 소셜 프루프 */}
      <div className="relative flex flex-col gap-10">
        <div>
          <h1
            className="m-0 whitespace-pre-line text-[2.5rem] leading-[1.2] font-bold tracking-[-0.03em] text-white"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {copy.heading}
          </h1>
          <p className="mt-4 text-base leading-relaxed text-white/70">
            {copy.sub}
          </p>
        </div>

        {/* 소셜 프루프 카드 */}
        <div
          role="group"
          aria-label="사용자 현황"
          className="rounded-[14px] border border-white/10 bg-white/[0.08] p-6 backdrop-blur"
        >
          {/* live indicator */}
          <div className="flex items-center gap-2.5 text-sm font-medium text-white/[0.88]">
            <span
              aria-hidden="true"
              className="relative inline-block h-2 w-2 flex-shrink-0 rounded-full bg-[#22c55e]"
            >
              <span
                className="absolute -inset-1 rounded-full bg-[#22c55e]/50 motion-safe:animate-ping"
                aria-hidden="true"
              />
            </span>
            <span>
              지금 <strong className="font-semibold text-white">7,234명</strong>
              이 실전 매매 중입니다
            </span>
          </div>

          {/* stats grid */}
          <div className="mt-4 grid grid-cols-2 gap-x-5 gap-y-3 border-t border-white/5 pt-4">
            {STATS.map((stat) => (
              <div
                key={stat.label}
                className="flex items-baseline gap-2 text-sm text-white/85"
              >
                <span
                  className="font-semibold text-white"
                  style={{ fontFamily: "var(--font-mono)" }}
                  data-type="number"
                >
                  {stat.value}
                </span>
                <span className="text-xs text-white/60">{stat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 인용문 */}
      <blockquote className="relative pl-7">
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
            fill="#fff"
          />
        </svg>
        <p
          className="m-0 mb-2.5 text-base leading-snug font-medium text-white/[0.92]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {copy.testimonialText}
        </p>
        <p className="text-sm text-white/60">
          <strong className="font-semibold text-white/[0.88]">
            {copy.testimonialAuthor}
          </strong>{" "}
          — {copy.testimonialRole}
        </p>
      </blockquote>
    </aside>
  );
}
