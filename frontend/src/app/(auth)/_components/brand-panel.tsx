// 인증 페이지 좌측 다크 브랜드 패널 — Sprint 42-polish-2 W1-fidelity
// design source: docs/prototypes/04-login.html (1:1 visual delta fix)

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

// prototype 04 의 5 사용자 avatar (initials + 그라디언트). hidden md+ 데스크톱 환경에서만 노출.
interface Avatar {
  initials: string;
  gradient: string;
}

const AVATARS: Avatar[] = [
  { initials: "JK", gradient: "linear-gradient(135deg, #2563EB, #1E40AF)" },
  { initials: "MH", gradient: "linear-gradient(135deg, #059669, #047857)" },
  { initials: "YS", gradient: "linear-gradient(135deg, #DC2626, #991B1B)" },
  { initials: "DW", gradient: "linear-gradient(135deg, #7C3AED, #5B21B6)" },
  { initials: "SJ", gradient: "linear-gradient(135deg, #EA580C, #9A3412)" },
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
      {/* 배경 장식 (radial gradient blobs) — prototype ::before / ::after */}
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

      {/* 로고 — fadeInUp 0.6s */}
      <Link
        href="/"
        aria-label="QuantBridge 홈으로 이동"
        className="auth-fade-in-1 relative inline-flex items-center gap-3 self-start"
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

      {/* 미들: 가치 제안 + 소셜 프루프 — fadeInUp 0.7s delay 0.1s */}
      <div className="auth-fade-in-2 relative flex flex-col gap-10">
        <div>
          <h1
            className="m-0 whitespace-pre-line text-[2.5rem] leading-[1.2] font-bold tracking-[-0.03em] text-white"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {copy.heading}
          </h1>
          <p className="mt-4 text-[1.05rem] leading-[1.6] text-white/70">
            {copy.sub}
          </p>
        </div>

        {/* 소셜 프루프 카드 — backdrop-blur + 14px radius + 24px padding */}
        <div
          role="group"
          aria-label="사용자 현황"
          className="rounded-[14px] border border-white/10 bg-white/[0.08] p-6 backdrop-blur"
        >
          {/* avatars row — prototype 5 colored circles, -8px overlap, mb=14px */}
          <div
            aria-hidden="true"
            data-testid="brand-avatars"
            className="mb-[14px] flex items-center"
          >
            {AVATARS.map((av, idx) => (
              <span
                key={av.initials}
                className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-[#1E293B] text-[0.82rem] font-bold text-white shadow-[0_2px_4px_rgba(0,0,0,0.2)]"
                style={{
                  background: av.gradient,
                  marginLeft: idx === 0 ? 0 : "-8px",
                  fontFamily: "var(--font-display)",
                }}
              >
                {av.initials}
              </span>
            ))}
          </div>

          {/* live indicator — prototype 의 정확한 pulse keyframe (livePulse) */}
          <div className="flex items-center gap-2.5 text-[0.92rem] font-medium text-white/[0.88]">
            <span
              aria-hidden="true"
              className="relative inline-block h-2 w-2 flex-shrink-0 rounded-full bg-[#22c55e]"
            >
              <span
                aria-hidden="true"
                className="absolute -inset-1 rounded-full bg-[#22c55e]/50 motion-safe:animate-[livePulse_2s_infinite]"
              />
            </span>
            <span>
              지금{" "}
              <strong className="font-semibold text-white">7,234명</strong>이
              실전 매매 중입니다
            </span>
          </div>

          {/* stats grid — prototype mt/pt = 18px (Tailwind arbitrary) + border-t white/8 */}
          <div className="mt-[18px] grid grid-cols-2 gap-x-5 gap-y-3 border-t border-white/[0.08] pt-[18px]">
            {STATS.map((stat) => (
              <div
                key={stat.label}
                className="flex items-baseline gap-2 text-[0.82rem] text-white/85"
              >
                <span
                  className="font-semibold text-white"
                  style={{ fontFamily: "var(--font-mono)" }}
                  data-type="number"
                >
                  {stat.value}
                </span>
                <span
                  className="text-[0.75rem] text-white/60"
                  style={{ fontFamily: "var(--font-sans)" }}
                >
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
            fill="#fff"
          />
        </svg>
        <p
          className="m-0 mb-2.5 text-[1.05rem] leading-[1.55] font-medium text-white/[0.92]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {copy.testimonialText}
        </p>
        <p className="text-[0.85rem] text-white/60">
          <strong className="font-semibold text-white/[0.88]">
            {copy.testimonialAuthor}
          </strong>{" "}
          — {copy.testimonialRole}
        </p>
      </blockquote>
    </aside>
  );
}
