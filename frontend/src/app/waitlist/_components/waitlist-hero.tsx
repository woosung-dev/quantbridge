// Sprint 43 W13 — /waitlist 좌측 hero 패널 (외부 첫인상 가치제안 + accent-amber illustration)
// design source: ui-ux-pro-max master "split-screen value prop" + DESIGN.md accent-amber 토큰
// 참고: brand-panel.tsx (Sprint 42-polish W1) split layout 패턴

import Link from "next/link";

interface ValueProp {
  title: string;
  description: string;
}

const VALUE_PROPS: ValueProp[] = [
  {
    title: "Pine Script 그대로 자동매매",
    description:
      "TradingView 알림을 webhook 으로 받아 Bybit / OKX 실거래까지. 코드 한 줄 수정 없이.",
  },
  {
    title: "백테스트는 7초",
    description:
      "고성능 벡터화 엔진. BTC 1년치 1m 봉 백테스트가 7초 안에 끝납니다.",
  },
  {
    title: "Beta 신청자에게만 공개",
    description:
      "현재 micro-cohort 운영 중. 안정화 단계라 매주 5-10명씩 초대장 발송.",
  },
];

interface BetaStat {
  value: string;
  label: string;
}

const BETA_STATS: BetaStat[] = [
  { value: "1-2주", label: "평균 대기" },
  { value: "Bybit + OKX", label: "지원 거래소" },
  { value: "Demo", label: "안전한 시작" },
];

export function WaitlistHero() {
  return (
    <aside
      aria-label="QuantBridge Beta 가치제안"
      className="relative hidden flex-col justify-between gap-10 overflow-hidden rounded-2xl p-12 text-[color:var(--text-primary)] lg:flex"
      style={{
        background:
          "linear-gradient(135deg, var(--accent-amber-light) 0%, #fef9c3 60%, #fde68a 100%)",
      }}
    >
      {/* 배경 장식 — accent-amber 그라디언트 blob */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-32 -right-32 h-[480px] w-[480px] rounded-full opacity-40"
        style={{
          background:
            "radial-gradient(circle, var(--accent-amber) 0%, transparent 70%)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-24 -left-24 h-[360px] w-[360px] rounded-full opacity-30"
        style={{
          background: "radial-gradient(circle, #fbbf24 0%, transparent 70%)",
        }}
      />

      <header className="relative z-10 space-y-4">
        <span className="inline-flex items-center gap-2 rounded-full bg-white/70 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-[color:var(--accent-amber)] backdrop-blur-sm">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--accent-amber)]" />
          Beta · Invite Only
        </span>
        <h1 className="font-display text-4xl font-extrabold leading-tight tracking-tight">
          Pine Script 전략을
          <br />
          <span className="text-[color:var(--accent-amber)]">실전 자동매매</span>로
        </h1>
        <p className="text-base leading-relaxed text-[color:var(--text-secondary)]">
          QuantBridge Beta 는 매주 5-10 명씩만 초대합니다. 신청서를 남기면 1-2 주 안에 회신 드립니다.
        </p>
      </header>

      <ul className="relative z-10 space-y-5">
        {VALUE_PROPS.map((prop, i) => (
          <li
            key={prop.title}
            className="flex items-start gap-3 motion-safe:animate-[fadeInUp_500ms_ease-out_both]"
            style={{ animationDelay: `${100 + i * 100}ms` }}
          >
            <span
              aria-hidden="true"
              className="mt-1 flex h-6 w-6 flex-none items-center justify-center rounded-full bg-[color:var(--accent-amber)] text-xs font-bold text-white"
            >
              ✓
            </span>
            <div className="space-y-1">
              <p className="font-semibold text-[color:var(--text-primary)]">
                {prop.title}
              </p>
              <p className="text-sm leading-relaxed text-[color:var(--text-secondary)]">
                {prop.description}
              </p>
            </div>
          </li>
        ))}
      </ul>

      <div className="relative z-10 grid grid-cols-3 gap-4 border-t border-[color:var(--accent-amber)]/20 pt-6">
        {BETA_STATS.map((stat) => (
          <div key={stat.label} className="space-y-1">
            <p className="font-display text-xl font-bold text-[color:var(--text-primary)]">
              {stat.value}
            </p>
            <p className="text-xs uppercase tracking-wide text-[color:var(--text-secondary)]">
              {stat.label}
            </p>
          </div>
        ))}
      </div>

      <p className="relative z-10 text-xs text-[color:var(--text-secondary)]">
        이미 계정이 있으신가요?{" "}
        <Link
          href="/sign-in"
          className="font-semibold text-[color:var(--accent-amber)] underline underline-offset-4"
        >
          로그인
        </Link>
      </p>
    </aside>
  );
}
