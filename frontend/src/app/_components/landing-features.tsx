// 랜딩 페이지 features 섹션 (3-col grid 6 카드 + section accent header)
import type { ReactNode } from "react";

interface FeatureItem {
  title: string;
  description: string;
  icon: ReactNode;
}

const FEATURES: FeatureItem[] = [
  {
    title: "Pine Script 파싱",
    description:
      "TradingView 전략을 자동으로 분석하고 Python으로 변환합니다. 복잡한 코딩 없이 전략을 즉시 활용하세요.",
    icon: (
      <>
        <polyline points="16,18 22,18 22,12" />
        <polyline points="8,6 2,6 2,12" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <polyline points="17,7 22,12 17,17" />
        <polyline points="7,7 2,12 7,17" />
      </>
    ),
  },
  {
    title: "벡터화 백테스트",
    description:
      "vectorbt 기반 초고속 백테스트로 수년간의 데이터를 초 단위로 검증합니다.",
    icon: <polygon points="13,2 3,14 12,14 11,22 21,10 12,10" />,
  },
  {
    title: "스트레스 테스트",
    description:
      "Monte Carlo, Walk-Forward 분석으로 전략의 실전 내구성을 검증합니다.",
    icon: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <polyline points="9,12 11,14 15,10" />
      </>
    ),
  },
  {
    title: "파라미터 최적화",
    description:
      "Grid, Bayesian, Genetic 알고리즘으로 최적의 파라미터를 자동 탐색합니다.",
    icon: (
      <>
        <line x1="4" y1="21" x2="4" y2="14" />
        <line x1="4" y1="10" x2="4" y2="3" />
        <line x1="12" y1="21" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12" y2="3" />
        <line x1="20" y1="21" x2="20" y2="16" />
        <line x1="20" y1="12" x2="20" y2="3" />
        <line x1="1" y1="14" x2="7" y2="14" />
        <line x1="9" y1="8" x2="15" y2="8" />
        <line x1="17" y1="16" x2="23" y2="16" />
      </>
    ),
  },
  {
    title: "데모 트레이딩",
    description: "실제 시장 데이터로 위험 없이 전략을 실전 테스트합니다.",
    icon: (
      <>
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </>
    ),
  },
  {
    title: "라이브 트레이딩",
    description:
      "CCXT 기반 100+ 거래소에서 자동 주문 실행. Kill Switch 내장으로 즉시 대응.",
    icon: <polyline points="22,12 18,12 15,21 9,3 6,12 2,12" />,
  },
];

export function LandingFeatures() {
  return (
    <section
      id="features"
      className="bg-[color:var(--bg)] px-6 py-20"
      aria-labelledby="features-heading"
    >
      <div className="mx-auto max-w-[1200px]">
        <div className="mb-12 text-center">
          <div
            aria-hidden
            className="mx-auto mb-4 h-[3px] w-12 rounded-sm bg-[color:var(--primary)]"
          />
          <h2
            id="features-heading"
            className="font-display text-[clamp(1.75rem,3vw,2.25rem)] font-bold text-[color:var(--text-primary)]"
          >
            핵심 기능
          </h2>
          <p className="mx-auto mt-3 max-w-[520px] text-base text-[color:var(--text-secondary)]">
            트레이딩 전략의 전체 라이프사이클을 하나의 플랫폼에서
          </p>
        </div>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <article
              key={f.title}
              className="rounded-[14px] bg-white p-7 shadow-[0_1px_3px_rgba(0,0,0,0.06),0_8px_24px_rgba(0,0,0,0.04)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_2px_8px_rgba(0,0,0,0.08),0_16px_40px_rgba(0,0,0,0.06)]"
            >
              <div className="flex size-11 items-center justify-center rounded-full bg-[color:var(--primary-light)]">
                <svg
                  aria-hidden
                  className="size-[22px]"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--primary)"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  {f.icon}
                </svg>
              </div>
              <h3 className="mt-4 font-display text-base font-semibold text-[color:var(--text-primary)]">
                {f.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[color:var(--text-secondary)]">
                {f.description}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
