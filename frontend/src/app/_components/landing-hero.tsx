// 랜딩 페이지 hero 섹션 (pill + h1 + underline svg + sub + CTA + trust avatars)
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { PnlTape } from "@/components/tape/pnl-tape";

// Precision Instrument: 아바타 = 플랫 스틸 칩 (구 브랜드 컬러 hex 폐기, 토큰 경유)
const TRUST_AVATARS = ["JK", "MH", "YS", "DW", "SJ"] as const;

// hero mockup 장식용 P&L tape 샘플 델타 (양수=bullish / 음수=bearish 마이크로바)
const HERO_TAPE_DELTAS = [
  3, 5, -2, 4, 6, -3, 2, 7, -1, 4, 5, -4, 3, 8, 2, -2, 6, 4, -3, 5, 7, -2, 4,
  6, 3, -1, 5, 8, -3, 6, 4, 7,
] as const;

export function LandingHero() {
  return (
    <section className="relative overflow-hidden bg-card px-6 pt-24 pb-20 md:pt-28 md:pb-24">
      {/* §6 플랫 원칙 — 미세 코퍼 radial 틴트 1개 (5%) */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(56% 44% at 72% 16%, color-mix(in srgb, var(--primary) 5%, transparent), transparent 70%)",
        }}
      />
      <div className="relative mx-auto grid max-w-[1200px] items-center gap-12 lg:grid-cols-[55%_45%]">
        <div className="flex flex-col">
          <div className="mb-6 inline-flex w-fit items-center gap-2 rounded-sm border border-[color:var(--primary-100)] bg-[color:var(--primary-light)] px-3.5 py-1.5 text-xs font-medium text-[color:var(--primary)]">
            <span className="size-1.5 rounded-full bg-[color:var(--primary)]" />
            v2.0 출시 — Monte Carlo 스트레스 테스트 지원
          </div>
          <h1 className="font-display text-[clamp(2.5rem,5vw,3.75rem)] font-extrabold leading-[1.15] tracking-[-0.01em] text-[color:var(--text-primary)]">
            Pine Script 전략을
            <br />
            <span className="relative inline-block">
              자동 트레이딩으로
              <svg
                aria-hidden
                className="absolute -bottom-1.5 left-0 w-full motion-safe:animate-[heroEntrance_700ms_cubic-bezier(0.34,1.56,0.64,1)_300ms_both]"
                viewBox="0 0 280 12"
                fill="none"
              >
                <path
                  d="M2 8C40 2 80 10 140 5C200 0 240 9 278 4"
                  stroke="var(--primary)"
                  strokeWidth="3"
                  strokeLinecap="round"
                  opacity="0.4"
                />
              </svg>
            </span>
          </h1>
          <p className="mt-5 max-w-[480px] text-lg leading-[1.7] text-[color:var(--text-secondary)] motion-safe:animate-[fadeInUp_500ms_ease-out_100ms_both]">
            {/* Sprint 61 T-8 (BL-322): hero copy ↔ 실제 기능 정합. 파일 업로드 / TV URL
                가져오기 "곧 지원" 상태이므로 "Pine Script 코드를 붙여넣으면" 으로 정직화. */}
            Pine Script 코드를 붙여넣으면 백테스트, 최적화, 스트레스 테스트를 거쳐 데모 또는 라이브 자동 매매까지 한 번에 연결됩니다.
          </p>
          <div className="mt-8 flex flex-wrap gap-3 motion-safe:animate-[fadeInUp_500ms_ease-out_200ms_both]">
            <Button
              size="lg"
              render={<Link href="/sign-up" />}
              nativeButton={false}
              className="shadow-btn-primary transition-all duration-200 hover:-translate-y-px hover:shadow-btn-primary-hover"
            >
              무료로 시작하기
              <svg
                aria-hidden
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="4" y1="9" x2="14" y2="9" />
                <polyline points="10,5 14,9 10,13" />
              </svg>
            </Button>
            <Button
              size="lg"
              variant="outline"
              render={<Link href="/sign-in" />}
              nativeButton={false}
              className="hover:border-[color:var(--primary)] hover:text-[color:var(--primary)]"
            >
              <svg
                aria-hidden
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polygon points="5,3 13,8 5,13" />
              </svg>
              라이브 데모
            </Button>
          </div>
          <div className="mt-8 flex items-center gap-4 motion-safe:animate-[fadeInUp_500ms_ease-out_300ms_both]">
            <div className="flex">
              {TRUST_AVATARS.map((initials) => (
                <span
                  key={initials}
                  className="-ml-2 flex size-8 items-center justify-center rounded-full border-2 border-card bg-[color:var(--bg-alt)] font-mono text-[0.6rem] font-semibold text-[color:var(--text-secondary)] first:ml-0"
                  aria-hidden
                >
                  {initials}
                </span>
              ))}
            </div>
            <span className="text-sm text-[color:var(--text-muted)]">
              Beta · 초기 dogfooder · feedback 환영
            </span>
          </div>
        </div>
        <HeroBrowserMockup />
      </div>
    </section>
  );
}

// 데스크톱 우측 브라우저 mockup — 차트 + P&L tape + KPI 3개.
// `dark` 스코프로 항상 카본/스틸/코퍼 제품 프리뷰 (라이트 테마에서도 다크 목업 유지).
function HeroBrowserMockup() {
  return (
    <div className="dark hidden overflow-hidden rounded-lg border border-[color:var(--border)] bg-card shadow-card motion-safe:animate-[heroFloat_6s_ease-in-out_infinite] lg:block">
      <div className="flex h-9 items-center gap-2 border-b border-[color:var(--border)] bg-muted px-3">
        <span className="size-2.5 rounded-full bg-bearish" />
        <span className="size-2.5 rounded-full bg-warning" />
        <span className="size-2.5 rounded-full bg-bullish" />
        <span className="ml-2 max-w-[260px] flex-1 truncate rounded-sm bg-[color:var(--bg-alt)] px-2.5 py-0.5 font-mono text-[0.7rem] text-[color:var(--text-muted)]">
          app.quantbridge.io/dashboard
        </span>
      </div>
      <div className="grid min-h-[280px] grid-cols-[60px_1fr] gap-3 bg-[color:var(--bg)] p-4">
        <div className="flex flex-col items-center gap-4 rounded-md bg-[color:var(--card)] py-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="size-7 rounded-md bg-[color:var(--bg-alt)]" />
          ))}
        </div>
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="font-display text-xs font-semibold text-[color:var(--text-primary)]">포트폴리오 개요</span>
            <div className="flex gap-1.5">
              <span className="rounded-sm border border-[color:var(--border)] bg-[color:var(--card)] px-2.5 py-1 text-[0.6rem] text-[color:var(--text-muted)]">
                Export
              </span>
              <span className="rounded-sm bg-[color:var(--primary)] px-2.5 py-1 text-[0.6rem] font-medium text-[color:var(--primary-foreground)]">
                +전략 추가
              </span>
            </div>
          </div>
          <svg viewBox="0 0 400 120" fill="none" className="w-full">
            <defs>
              <linearGradient id="heroChartGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--chart-equity)" stopOpacity="0.25" />
                <stop offset="100%" stopColor="var(--chart-equity)" stopOpacity="0" />
              </linearGradient>
            </defs>
            <text x="0" y="15" fill="var(--chart-axis)" fontSize="8" fontFamily="var(--font-mono)">$130K</text>
            <text x="0" y="40" fill="var(--chart-axis)" fontSize="8" fontFamily="var(--font-mono)">$120K</text>
            <text x="0" y="65" fill="var(--chart-axis)" fontSize="8" fontFamily="var(--font-mono)">$110K</text>
            <text x="0" y="90" fill="var(--chart-axis)" fontSize="8" fontFamily="var(--font-mono)">$100K</text>
            <path
              d="M40,85 L60,80 L80,78 L100,72 L120,75 L140,65 L160,60 L180,55 L200,58 L220,50 L240,45 L260,40 L280,35 L300,30 L320,25 L340,22 L360,18 L380,15"
              stroke="var(--chart-equity)"
              strokeWidth="2"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M40,85 L60,80 L80,78 L100,72 L120,75 L140,65 L160,60 L180,55 L200,58 L220,50 L240,45 L260,40 L280,35 L300,30 L320,25 L340,22 L360,18 L380,15 L380,100 L40,100 Z"
              fill="url(#heroChartGrad)"
            />
          </svg>
          {/* Precision Instrument 시그니처 — P&L tape 마이크로바 (장식) */}
          <PnlTape
            deltas={HERO_TAPE_DELTAS}
            maxBars={32}
            size="micro"
            className="opacity-80"
          />
          <div className="grid grid-cols-3 gap-2">
            <MockStat label="Total" value="—" />
            <MockStat label="Today" value="—" tone="green" />
            <MockStat label="Win Rate" value="—" />
          </div>
        </div>
      </div>
    </div>
  );
}

function MockStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "green";
}) {
  return (
    <div className="rounded-md border border-[color:var(--border)] bg-[color:var(--card)] p-2.5">
      <div className="mb-0.5 font-mono text-[0.6rem] tracking-[0.08em] text-[color:var(--text-muted)] uppercase">{label}</div>
      <div
        className="font-mono text-sm font-semibold tabular-nums"
        style={{
          color: tone === "green" ? "var(--bullish)" : "var(--text-primary)",
        }}
      >
        {value}
      </div>
    </div>
  );
}
